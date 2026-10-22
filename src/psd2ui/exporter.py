import json
import logging
import math
import tempfile
from contextlib import contextmanager
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage
from psd_tools.composite import composite_pil
from psd_tools.constants import BlendMode, ColorMode, Tag

from .diagnostics import Diagnostics, ExportError
from .deduplication import deduplicate_images, similarity_threshold
from .naming import export_name, inside, is_variable_name, layer_tag, tag_component, untagged_name
from .laya_types import component_layout
from .layout import layout_gap, ordered_children
from .text import text_bounds, text_properties


def union(boxes):
    boxes = [b for b in boxes if b is not None and b[2] > b[0] and b[3] > b[1]]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def visual_warnings(layer, diagnostics, path, flattened=False):
    reasons = []
    if layer.blend_mode not in (BlendMode.NORMAL, BlendMode.PASS_THROUGH):
        reasons.append(f"blend mode {layer.blend_mode.name} requires a backdrop")
    if layer.is_group() and layer.blend_mode == BlendMode.PASS_THROUGH and not flattened:
        reasons.append("pass-through group becomes an isolated runtime container")
    if layer.clipping or layer.has_clip_layers():
        reasons.append("clipping masks may depend on sibling layers")
    if layer.kind not in ("pixel", "group", "type"):
        reasons.append(f"{layer.kind} uses cached pixels or limited psd-tools rendering")
    effects = [e.name for e in layer.effects if layer.effects.enabled and e.enabled]
    if effects:
        reasons.append("layer effects are approximate/partially supported: " + ", ".join(effects))
    if layer.is_group() and (layer.has_mask() or layer.has_vector_mask()):
        reasons.append("group masks cannot be mapped to a plain container" if not flattened else "group mask compositing is library-dependent")
    if layer.kind == "type" and not flattened and (layer.has_mask() or layer.has_vector_mask()):
        reasons.append("text masks cannot be mapped to runtime text")
    if layer.kind == "type" and not flattened and layer.tagged_blocks.get_data(Tag.BLEND_FILL_OPACITY, 255) != 255:
        reasons.append("text fill opacity independent of its effects is not mapped")
    if layer.is_group() and not flattened and layer.opacity != 255:
        reasons.append("group opacity is applied as runtime container alpha; overlapping children can differ")
    if reasons:
        diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", path, "; ".join(reasons))


def included(layer, target):
    """Ignore only target visibility; descendants retain local visibility and # filtering."""
    current = layer
    while current is not target:
        if current is None or not hasattr(current, "name") or "#" in current.name or not current.visible:
            return False
        current = current.parent
    return "#" not in target.name


@contextmanager
def render_state(target):
    """Restore all PSD state even on failure; never save modifications to source."""
    changed = []
    current = target
    while current is not None and not isinstance(current, PSDImage):
        changed.append((current, current.visible))
        current.visible = True
        current = current.parent
    excluded = []
    if target.is_group():
        for layer in target.descendants():
            if "#" in layer.name:
                excluded.append((layer, layer.visible))
                layer.visible = False
    clipping = target.clipping
    if clipping:
        target.clipping = False
    try:
        yield
    finally:
        if clipping:
            target.clipping = clipping
        for layer, visible in reversed(excluded + changed):
            layer.visible = visible


def render_bounds(layer, target):
    if not included(layer, target):
        return None
    box = union(render_bounds(child, target) for child in layer) if layer.is_group() else layer.bbox
    if box is None or box[2] <= box[0] or box[3] <= box[1]:
        return None
    # This is a temporary rendering viewport, not the final PNG bounds. Even
    # inset strokes need an outside margin for the renderer to detect the edge.
    # Completely transparent margins are removed after effects are composited.
    padding = math.ceil(max((float(e.size) for e in layer.effects
                            if layer.effects.enabled and e.enabled and e.name == "Stroke"), default=0))
    return (box[0] - padding, box[1] - padding, box[2] + padding, box[3] + padding)


class _LibraryWarnings(logging.Handler):
    def __init__(self, diagnostics, path):
        super().__init__(logging.WARNING)
        self.diagnostics, self.path, self.messages = diagnostics, path, set()

    def emit(self, record):
        message = record.getMessage()
        if message not in self.messages:
            self.messages.add(message)
            self.diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", self.path, "psd-tools: " + message)


@contextmanager
def capture_library_warnings(diagnostics, path):
    logger = logging.getLogger("psd_tools")
    handler = _LibraryWarnings(diagnostics, path)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)


class Exporter:
    def __init__(self, output, diagnostics=None):
        self.output = Path(output)
        self.diagnostics = diagnostics if diagnostics is not None else Diagnostics()
        self.asset_nodes = {}

    def node(self, layer, folders=(), ancestry=(), title_context=False):
        raw = layer.name
        if "#" in raw:
            return None
        path = "/".join((*ancestry, raw))
        component = tag_component(raw)
        text_fallback = layer.kind == "type" and (component is None or not is_variable_name(untagged_name(raw)))
        try:
            name = ("title" if title_context else "text") if text_fallback else export_name(raw)
        except ValueError as exc:
            self.diagnostics.fail("INVALID_EXPORT_NAME", path, str(exc))
        # Group layer styles operate on the composed group, so bake the whole
        # group just like img_. Disabled styles do not change its structure.
        tag = layer_tag(raw)
        layout = component_layout(raw.partition("_")[0]) if tag else None
        flattened = component in ("GImage", "GLoader") or (
            layer.is_group() and layer.effects.enabled and any(effect.enabled for effect in layer.effects)
        )
        visual_warnings(layer, self.diagnostics, path, flattened)
        node = {"name": name, "visible": bool(layer.visible)}
        if layer.is_group() and not flattened:
            inside(self.output, "/".join(("assets", *folders, name))).mkdir(parents=True, exist_ok=True)
            children = []
            # psd-tools >=1.7 iterates background -> foreground. Do NOT reverse.
            for child in layer:
                item = self.node(child, (*folders, name), (*ancestry, raw),
                                 title_context or component in ("GButton", "GProgressBar"))
                if item is not None:
                    children.append(item)
            node.update(type="container", children=children)
            if component:
                node["component"] = component
            if layout:
                node["layout"] = layout
            if layer.opacity != 255:
                node["opacity"] = layer.opacity / 255
            # Empty groups have a real record origin; no visible-only group bbox is used.
            node["_box"] = (layer._record.left, layer._record.top, layer._record.right, layer._record.bottom)
        elif layer.kind == "type" and not flattened:
            box = text_bounds(layer, self.diagnostics, path)
            if box[2] <= box[0] or box[3] <= box[1]:
                self.diagnostics.fail("INVALID_BOUNDS", path, f"Text has no trustworthy bounds: {box}")
            node.update(type="text", _box=box, **text_properties(layer, self.diagnostics, path))
        else:
            if flattened and layer.is_group():
                for child in layer.descendants():
                    if included(child, layer):
                        visual_warnings(child, self.diagnostics, path + "/" + child.name, True)
            box = render_bounds(layer, layer)
            if box is None:
                # PNG cannot represent 0x0. Preserve the empty layer, don't invent a 1x1 asset.
                raw_box = (layer._record.left, layer._record.top, layer._record.right, layer._record.bottom)
                if raw_box[2] != raw_box[0] or raw_box[3] != raw_box[1]:
                    if not layer.is_group():
                        self.diagnostics.fail("INVALID_BOUNDS", path, f"Cannot render bounds: {raw_box}")
                self.diagnostics.warn("EMPTY_LAYER", path, "No drawable pixels; preserved as a zero-sized empty container")
                node.update(type="container", children=[], _box=(raw_box[0], raw_box[1], raw_box[0], raw_box[1]))
                if component:
                    node["component"] = component
                if layout:
                    node["layout"] = layout
                return node
            render_origin = box[:2]
            try:
                with render_state(layer), capture_library_warnings(self.diagnostics, path):
                    image = composite_pil(layer, color=1.0, alpha=0.0, viewport=box,
                                          layer_filter=lambda item: included(item, layer),
                                          force=False, as_layer=True)
                if image is None:
                    raise ValueError("psd-tools returned no composite")
                image = image.convert("RGBA")
                if image.size != (box[2] - box[0], box[3] - box[1]):
                    raise ValueError("Composite size differs from requested bounds")
                # PSD raster caches can contain uneven transparent padding,
                # including 1px differences between identical vector shapes.
                # Crop only alpha == 0: retain every antialiased/effect pixel,
                # and compensate the absolute origin before deriving local
                # positions and parent bounds. Never round vector geometry or
                # resize raster pixels to force a particular logical size.
                ink = image.getchannel("A").getbbox()
                if ink is not None:
                    image = image.crop(ink)
                    box = (box[0] + ink[0], box[1] + ink[1],
                           box[0] + ink[2], box[1] + ink[3])
                # An entirely transparent image keeps its original canvas;
                # there is no nonempty crop, and PNG cannot represent 0x0.
            except Exception as exc:
                self.diagnostics.fail("COMPOSITE_FAILED", path, f"{type(exc).__name__}: {exc}")
            asset = "/".join(("assets", *folders, name + ".png"))
            destination = inside(self.output, asset)
            destination.parent.mkdir(parents=True, exist_ok=True)
            node.update(type="image", asset=asset, _box=box, _render_origin=render_origin)
            if asset in self.asset_nodes:
                self.diagnostics.warn("DUPLICATE_ASSET_PATH", path, f"Overwriting {asset}; all references use the last PNG")
                # The last PNG also determines crop offsets for every reference.
                # Earlier layers may have had different transparent margins;
                # applying their own crop offset would move the replacement art.
                dx, dy = box[0] - render_origin[0], box[1] - render_origin[1]
                for previous in self.asset_nodes[asset]:
                    x, y = previous["_render_origin"]
                    x, y = x + dx, y + dy
                    previous["_box"] = (x, y, x + image.width, y + image.height)
            self.asset_nodes.setdefault(asset, []).append(node)
            # composite_pil already converts through the source ICC profile to sRGB.
            # Pillow's generated sRGB ICC includes a creation timestamp. Do not embed
            # that volatile metadata: identical PSDs must produce identical PNG bytes.
            image.info.clear()
            image.save(destination, format="PNG")
        direct_component = (node["type"] == "image" and component in ("GImage", "GLoader") or
                            node["type"] == "text" and component in ("GTextField", "GTextInput"))
        if direct_component:
            node["component"] = component
        elif component and node["type"] != "container":
            # A typed leaf keeps its original editable text/image as a static
            # child. Native controls need not guess skins, labels or states.
            visual = node
            visual["name"] = (("title" if title_context or component in ("GButton", "GProgressBar") else "text")
                              if text_fallback and visual["type"] == "text" else name + "_content")
            visual["visible"] = True
            node = dict(name=name, visible=bool(layer.visible), type="container",
                        component=component, children=[visual], _box=visual["_box"])
            if layout:
                node["layout"] = layout
        return node

    def finalize(self, node, origin=(0, 0)):
        node.pop("_render_origin", None)
        if node["type"] == "container":
            boxes = [self.absolute_box(child) for child in node["children"]]
            node["_box"] = union(boxes) or node["_box"]
        box = node.pop("_box")
        node["position"] = [box[0] - origin[0], box[1] - origin[1]]
        node["size"] = [box[2] - box[0], box[3] - box[1]]
        for child in node.get("children", []):
            self.finalize(child, box[:2])
        if "layout" in node:
            node["children"] = ordered_children(node["children"], node["layout"])
            node["gap"], uneven = layout_gap(node["children"], node["layout"])
            if uneven:
                self.diagnostics.warn("NON_UNIFORM_LAYOUT_GAP", node["name"],
                    f"PSD child gaps differ; native {node['layout']} layout uses mean gap {node['gap']}")

    def absolute_box(self, node):
        if node["type"] == "container":
            node["_box"] = union(self.absolute_box(child) for child in node["children"]) or node["_box"]
        return node["_box"]

    def build(self, source):
        with capture_library_warnings(self.diagnostics, str(source)):
            psd = PSDImage.open(source)
        if psd.color_mode != ColorMode.RGB or psd.depth != 8:
            self.diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", str(source),
                                  f"Color mode {psd.color_mode.name}/{psd.depth}-bit converted to 8-bit RGBA")
        children = []
        for layer in psd:
            node = self.node(layer)
            if node is not None:
                children.append(node)
        for child in children:
            self.finalize(child)
        root = dict(version=1, name=Path(source).stem, type="root", position=[0, 0],
                    size=[psd.width, psd.height], visible=True, children=children)
        self.validate(root)
        return root

    def validate(self, node):
        if node["type"] == "image":
            try:
                with Image.open(inside(self.output, node["asset"])) as image:
                    if list(image.size) != node["size"]:
                        raise ValueError(f"PNG size {image.size} != node size {node['size']}")
            except Exception as exc:
                self.diagnostics.fail("MISSING_ASSET", node["asset"], str(exc))
        for child in node.get("children", []):
            self.validate(child)


def export_psd(source, output, diagnostics=None, *, dedupe_images=None):
    """Stage a complete export before publishing layout.json (the success marker).

    Only paths produced by this export are replaced or, when deduplication is
    enabled, deleted. On rendering failure previous output remains valid.
    """
    if dedupe_images is not None:
        dedupe_images = similarity_threshold(dedupe_images)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".psd2ui-", dir=output) as stage:
        exporter = Exporter(stage, diagnostics)
        root = exporter.build(source)
        duplicates = deduplicate_images(root, stage, dedupe_images) if dedupe_images is not None else {}
        # Validate rewritten references and resolve every destination before publishing.
        exporter.validate(root)
        destinations = {asset: inside(output, asset) for asset in exporter.asset_nodes}
        if duplicates and len(set(destinations.values())) != len(destinations):
            raise ValueError("PNG output paths alias one another through symbolic links")
        for asset in exporter.asset_nodes:
            if asset in duplicates:
                continue
            destination = destinations[asset]
            destination.parent.mkdir(parents=True, exist_ok=True)
            inside(Path(stage), asset).replace(destination)
        # Preserve ordinary group directories, including empty ones.
        for directory in sorted(Path(stage).rglob("*")):
            if directory.is_dir():
                inside(output, directory.relative_to(stage).as_posix()).mkdir(parents=True, exist_ok=True)
        exporter.output = output
        exporter.validate(root)
        staged_layout = Path(stage) / "layout.json"
        staged_layout.write_text(json.dumps(root, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        staged_layout.replace(output / "layout.json")
        # Publish references first so no current layout points at a deleted PNG.
        # Also remove redundant files left by an earlier non-deduplicated export.
        for asset in duplicates:
            (output / asset).unlink(missing_ok=True)
    return root

