import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from psd_tools import PSDImage
from psd_tools.constants import Tag
from psd_tools.psd.tagged_blocks import TaggedBlock
from psd_tools.psd.layer_and_mask import ChannelDataList
from psd_tools.psd.vector import ClosedKnotLinked, ClosedPath, InitialFillRule, Path as VectorPath, PathFillRule, VectorMaskSetting

from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel, text


def create_group_mask(parent, image, *, top=0, left=0):
    # Group.new in psd-tools 1.17.4 aliases the folder and closing-divider
    # channel lists. A mask channel belongs only to the folder record.
    parent._bounding_channels = ChannelDataList(list(parent._bounding_channels))
    mask = parent.create_mask(image, top=top, left=left)
    parent._psd._update_record()
    return mask


@pytest.mark.parametrize("kind", ["pixel", "vector"])
@pytest.mark.parametrize("name,component", [("Masked", None), ("icon_Masked", "GLoader"), ("btn_Masked", "GButton")])
def test_masked_group_bakes_mask_and_descendants_into_one_png(tmp_path, kind, name, component):
    psd = PSDImage.new("RGBA", (100, 100))
    parent = group(psd, name, visible=False)
    pixel(parent, "Base", "red", (10, 10), (60, 60))
    text(parent, "Caption", "Baked", (15, 15))
    pixel(parent, "#Ignored", "lime", (10, 10), (60, 60))
    pixel(parent, "Hidden", "blue", (10, 10), (60, 60), visible=False)
    # Keep only a 20 x 20 square, well away from any text glyphs.
    if kind == "pixel":
        mask = Image.new("L", (100, 100))
        ImageDraw.Draw(mask).rectangle((40, 40, 59, 59), fill=255)
        create_group_mask(parent, mask)
    else:
        knots = [ClosedKnotLinked(preceding=p, anchor=p, leaving=p)
                 for p in ((.4, .4), (.4, .6), (.6, .6), (.6, .4))]
        parent.tagged_blocks[Tag.VECTOR_MASK_SETTING1] = TaggedBlock(
            key=Tag.VECTOR_MASK_SETTING1,
            data=VectorMaskSetting(path=VectorPath([PathFillRule(), InitialFillRule(0), ClosedPath(knots)])))
    source = tmp_path / "mask.psd"
    psd.save(source)
    output = tmp_path / "out"
    root = export_psd(source, output)
    node = root["children"][0]
    assert not node["visible"]
    visual = node["children"][0] if component == "GButton" else node
    assert visual["type"] == "image" and "children" not in visual
    assert list(output.rglob("*.png")) == [output / visual["asset"]]
    if component == "GButton":
        assert node["component"] == "GButton" and len(node["children"]) == 1
    else:
        assert node.get("component") == component
    # Reconstruct the image in document coordinates and assert masked pixels.
    origin = node["position"]
    if visual is not node:
        origin = [a + b for a, b in zip(origin, visual["position"])]
    canvas = Image.new("RGBA", psd.size)
    with Image.open(output / visual["asset"]) as png:
        canvas.paste(png, tuple(origin))
    assert canvas.getpixel((50, 50)) == (255, 0, 0, 255)
    assert canvas.getpixel((20, 50))[3] == 0
    assert canvas.getpixel((65, 50))[3] == 0
    project = tmp_path / "project"
    project.mkdir()
    generated = generate_prefab(output / "layout.json", project)
    assert generated["images"] == 1 and generated["texts"] == 0
    native = json.loads(Path(generated["prefab"]).read_text())["_$child"][0]
    assert native["_$type"] == (component or "GImage")


def test_disabled_mask_group_still_flattens_and_hash_excludes_it(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    for name in ("Disabled", "#Excluded"):
        parent = group(psd, name)
        pixel(parent, "Base", "red", (10, 10), (20, 20))
        create_group_mask(parent, Image.new("L", (20, 20)), top=10, left=10).disabled = True
    source = tmp_path / "disabled.psd"
    psd.save(source)
    output = tmp_path / "out"
    root = export_psd(source, output)
    assert len(root["children"]) == 1
    node = root["children"][0]
    assert node["type"] == "image" and "children" not in node
    assert node["size"] == [20, 20]
    with Image.open(output / node["asset"]) as png:
        assert png.getpixel((0, 0)) == (255, 0, 0, 255)
