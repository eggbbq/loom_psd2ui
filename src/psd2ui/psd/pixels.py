"""Composite one PSD layer with its own full canvas and local child states."""
from contextlib import contextmanager
import logging
import math

from psd_tools.composite import composite_pil
from psd_tools.constants import ColorMode, Resource
from psd_tools import PSDImage
from psd2ui.color import apply_icc


def union(boxes):
    boxes = [box for box in boxes if box and box[2] > box[0] and box[3] > box[1]]
    if not boxes:
        return (0, 0, 0, 0)
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def cached_bounds(layer, *, trim_static_smartobjects=False):
    """Optional static cache trim; never trim fully transparent sizing records."""
    if trim_static_smartobjects is not False and layer.kind == 'smartobject':
        image = layer.topil()
        if image is not None and 'A' in image.getbands():
            box = image.getchannel('A').getbbox()
            if box:
                x, y = layer.bbox[:2]
                if trim_static_smartobjects is None:
                    full=image.width*image.height;occupied=(box[2]-box[0])*(box[3]-box[1])
                    if full<4*occupied:return layer.bbox
                return (x+box[0], y+box[1], x+box[2], y+box[3])
    return layer.bbox


def content_bounds(layer, *, local_visibility=False, trim_static_smartobjects=False):
    if '#' in layer.name or (local_visibility and not layer.visible):
        return (0, 0, 0, 0)
    if layer.is_group():
        trim = False if layer.name.partition('_')[0]=='icon' else trim_static_smartobjects
        return union(content_bounds(child, local_visibility=local_visibility,
                                    trim_static_smartobjects=trim) for child in layer)
    return cached_bounds(layer, trim_static_smartobjects=trim_static_smartobjects)


def render_bounds(layer, *, target=True, trim_static_smartobjects=False):
    if '#' in layer.name or (not target and not layer.visible):
        return (0, 0, 0, 0)
    trim = False if layer.name.partition('_')[0]=='icon' else trim_static_smartobjects
    box = (union(render_bounds(child, target=False, trim_static_smartobjects=trim) for child in layer)
           if layer.is_group() else cached_bounds(layer, trim_static_smartobjects=trim))
    if box[2] <= box[0] or box[3] <= box[1]:
        return box
    padding = 0
    for effect in layer.effects:
        if layer.effects.enabled and effect.enabled:
            padding = max(padding, math.ceil(abs(float(getattr(effect, 'size', 0)))
                                           + abs(float(getattr(effect, 'distance', 0))) + 2))
    return (box[0]-padding, box[1]-padding, box[2]+padding, box[3]+padding)


def included(layer, target):
    current = layer
    while current is not target:
        if current is None or '#' in current.name or not current.visible:
            return False
        current = current.parent
    return '#' not in target.name


class WarningCapture(logging.Handler):
    def __init__(self, callback, path):
        super().__init__(logging.WARNING)
        self.callback, self.path = callback, path

    def emit(self, record):
        self.callback('PSD_RENDER_WARNING', self.path, record.getMessage())


@contextmanager
def render_state(target):
    changed = []
    current = target
    # Only in-memory flags are temporarily changed. No source file is saved.
    while current is not None and not isinstance(current, PSDImage):
        changed.append((current, current.visible))
        current.visible = True
        current = getattr(current, 'parent', None)
    try:
        yield
    finally:
        for layer, visible in reversed(changed):
            layer.visible = visible


def render(layer, viewport, warn, path):
    handler = WarningCapture(warn, path)
    logger = logging.getLogger('psd_tools')
    logger.addHandler(handler)
    try:
        psd = layer._psd
        profile = (psd.image_resources.get_data(Resource.ICC_PROFILE)
                   if psd.color_mode == ColorMode.RGB and Resource.ICC_PROFILE in psd.image_resources else None)
        with render_state(layer):
            image = composite_pil(layer, viewport=viewport, color=1.0, alpha=0.0,
                                  layer_filter=lambda item: included(item, layer),
                                  force=False, as_layer=True, apply_icc=not bool(profile))
            if image is not None and profile:
                image = apply_icc(image, profile)
        if image is None:
            raise ValueError(f'psd-tools 无法合成图片：{path}')
        result = image.convert('RGBA')
        if result.size != (viewport[2]-viewport[0], viewport[3]-viewport[1]):
            raise ValueError(f'psd-tools 合成尺寸与请求不一致：{path}')
        return result
    finally:
        logger.removeHandler(handler)
