import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.terminology import Key

from psd2ui.exporter import export_psd, included, render_bounds, render_state
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel, text
from tests.test_group_effects import add_effect


def image_nodes(node, origin=(0, 0)):
    x, y = (a + b for a, b in zip(origin, node["position"]))
    if node["type"] == "image":
        yield node, (x, y)
    for child in node.get("children", []):
        yield from image_nodes(child, (x, y))


def test_bg_item_cached_padding_does_not_change_size_or_deduplication(tmp_path):
    psd = PSDImage.new("RGBA", (500, 300))
    for name, left, width, inset in (("First", 60, 103, 1), ("Second", 274, 104, 2)):
        styled = group(group(psd, name), "bg_item")
        image = Image.new("RGBA", (width, 103))
        ImageDraw.Draw(image).rectangle((inset, 2, inset + 99, 101), fill="red")
        PixelLayer.frompil(image, parent=styled, name="Shape", left=left, top=30)
        add_effect(styled)
        next(iter(styled.effects)).descriptor[Key.Style].enum = b"InsF"
    source = tmp_path / "padded.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output, dedupe_images=1)
    images = list(image_nodes(layout))
    assert [node["size"] for node, _ in images] == [[100, 100], [100, 100]]
    assert [origin for _, origin in images] == [(61, 32), (276, 32)]
    assert images[0][0]["asset"] == images[1][0]["asset"]
    assert len(list((output / "assets").rglob("*.png"))) == 1
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(output / "layout.json", project)
    assert result["textures"] == 1
    native = json.loads(Path(result["prefab"]).read_text())
    assert [p["width"] for p in native["_$child"]] == [100, 100]
    assert [p["x"] for p in native["_$child"]] == [61, 276]


@pytest.mark.parametrize("style", [b"InsF", b"CtrF", b"OutF"])
def test_trimming_keeps_every_rendered_effect_pixel_in_document_position(tmp_path, style):
    from psd_tools.composite import composite_pil
    psd = PSDImage.new("RGBA", (100, 100))
    styled = group(psd, "btn_Styled", visible=False, opacity=128)
    pixel(styled, "Base", "red", (30, 35), (20, 18))
    add_effect(styled)
    next(iter(styled.effects)).descriptor[Key.Style].enum = style
    box = render_bounds(styled, styled)
    with render_state(styled):
        rendered = composite_pil(styled, color=1.0, alpha=0.0, viewport=box,
                                 layer_filter=lambda item: included(item, styled),
                                 force=False, as_layer=True).convert("RGBA")
    before = Image.new("RGBA", psd.size)
    before.paste(rendered, box[:2])
    source = tmp_path / "stroke.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output)
    node, position = next(image_nodes(layout))
    with Image.open(output / node["asset"]) as png:
        after = Image.new("RGBA", psd.size)
        after.paste(png, position)
    a, b = np.asarray(before), np.asarray(after)
    np.testing.assert_array_equal(a[:, :, 3], b[:, :, 3])
    np.testing.assert_array_equal(a[a[:, :, 3] > 0], b[b[:, :, 3] > 0])
    assert layout["children"][0]["component"] == "GButton"
    assert not layout["children"][0]["visible"]


def test_trimming_preserves_alpha_one_and_editable_text_geometry(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    parent = group(psd, "Panel")
    image = Image.new("RGBA", (12, 10))
    ImageDraw.Draw(image).rectangle((2, 3, 8, 7), fill=(20, 40, 60, 255))
    image.putpixel((1, 2), (1, 2, 3, 1))
    PixelLayer.frompil(image, parent=parent, name="icon_Edge", left=-5, top=8)
    text(parent, "title_Caption", "UI", xy=(20, 30))
    source = tmp_path / "alpha.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output)
    node, position = next(image_nodes(layout))
    assert node["size"] == [8, 6] and position == (-4, 10)
    assert node["component"] == "GLoader"
    with Image.open(output / node["asset"]) as image:
        assert image.getpixel((0, 0))[3] == 1
    panel = layout["children"][0]
    caption = panel["children"][1]
    assert caption["type"] == "text" and caption["text"] == "UI"
    assert [panel["position"][i] + caption["position"][i] for i in (0, 1)] == [20, 30]


def test_fully_transparent_image_keeps_valid_nonzero_canvas(tmp_path):
    psd = PSDImage.new("RGBA", (40, 40))
    pixel(psd, "Invisible", "red", (10, 12), (7, 9), opacity=0)
    source = tmp_path / "transparent.psd"
    psd.save(source)
    output = tmp_path / "out"
    node = export_psd(source, output)["children"][0]
    assert node["type"] == "image" and node["size"] == [7, 9]
    assert node["position"] == [10, 12]
    with Image.open(output / node["asset"]) as image:
        assert image.size == (7, 9) and image.getchannel("A").getbbox() is None


def test_same_path_overwrite_uses_final_png_crop_offset_for_all_references(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    for origin, inset, color in ((10, (1, 1), "red"), (20, (2, 3), "blue")):
        image = Image.new("RGBA", (8, 8))
        ImageDraw.Draw(image).rectangle((*inset, inset[0] + 3, inset[1] + 2), fill=color)
        PixelLayer.frompil(image, parent=psd, name="same", left=origin, top=origin)
    source = tmp_path / "overwrite.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output)
    first, second = layout["children"]
    assert first["asset"] == second["asset"]
    assert first["size"] == second["size"] == [4, 3]
    assert first["position"] == [12, 13]
    assert second["position"] == [22, 23]
    assert "_render_origin" not in first and "_render_origin" not in second
    with Image.open(output / first["asset"]) as png:
        assert png.getpixel((0, 0)) == (0, 0, 255, 255)
