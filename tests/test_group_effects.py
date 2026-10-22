import pytest
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import Tag
from psd_tools.psd.descriptor import Bool, Descriptor, DescriptorBlock2, Double, Enumerated
from psd_tools.psd.tagged_blocks import TaggedBlock
from psd_tools.terminology import Key, Klass

from psd2ui.diagnostics import Diagnostics, ExportError
from psd2ui.exporter import export_psd
from tests.fixture_factory import group, pixel, text


def add_effect(layer, kind="Stroke", enabled=True, master=True):
    effect = Descriptor(classID={"Stroke": Klass.FrameFX.value, "OuterGlow": Klass.OuterGlow.value}[kind],
        items={Key.Enabled: Bool(enabled), b"present": Bool(True), Key.Opacity: Double(100),
               Key.Color: Descriptor(classID=Klass.RGBColor.value,
                   items={b"Rd  ": Double(0), b"Grn ": Double(0), b"Bl  ": Double(0)}),
               Key.SizeKey: Double(2), Key.Blur: Double(3),
               Key.PaintType: Enumerated(typeID=b"FrFl", enum=b"SClr"),
               Key.Style: Enumerated(typeID=b"FStl", enum=b"OutF")})
    layer.tagged_blocks[Tag.OBJECT_BASED_EFFECTS_LAYER_INFO] = TaggedBlock(
        key=Tag.OBJECT_BASED_EFFECTS_LAYER_INFO,
        data=DescriptorBlock2(items={b"masterFXSwitch": Bool(master), b"effect": effect}))


@pytest.mark.parametrize("kind", ["Stroke", "OuterGlow"])
@pytest.mark.parametrize("visible", [True, False])
def test_group_style_is_one_image_with_filtering_and_baked_opacity(tmp_path, kind, visible):
    psd = PSDImage.new("RGBA", (160, 120))
    parent = group(psd, "Panel", visible=False)
    styled = group(parent, "Styled", visible=visible, opacity=128)
    pixel(styled, "Base", "red", (20, 30), (80, 60))
    text(styled, "Merged text", value="UI", xy=(30, 40))
    pixel(styled, "Hidden", "blue", (20, 30), (80, 60), visible=False)
    pixel(styled, "Reference#", "lime", (-20, -10), (150, 120))
    ignored = group(styled, "Ignore# subtree")
    pixel(ignored, "Excluded", "magenta", (20, 30), (80, 60))
    add_effect(styled, kind)
    source = tmp_path / "effects.psd"
    psd.save(source)
    diagnostics = Diagnostics()
    output = tmp_path / "out"
    root = export_psd(source, output, diagnostics)
    panel = root["children"][0]
    image = panel["children"][0]
    assert panel["type"] == "container" and not panel["visible"]
    assert image["type"] == "image" and image["visible"] == visible
    assert image["name"] == "Styled" and image["asset"] == "assets/Panel/Styled.png"
    assert "children" not in image and "opacity" not in image
    assert not (output / "assets/Panel/Styled").exists()
    assert list(output.rglob("*.png")) == [output / image["asset"]]
    png = Image.open(output / image["asset"])
    x = 21 - panel["position"][0] - image["position"][0]
    y = 31 - panel["position"][1] - image["position"][1]
    assert png.getpixel((x, y)) == (255, 0, 0, 128)
    assert list(png.size) == image["size"]
    assert any(d.code == "UNSUPPORTED_VISUAL_EFFECT" and kind in d.message for d in diagnostics.items)


@pytest.mark.parametrize("enabled,master", [(False, True), (True, False), (False, False)])
def test_disabled_group_styles_preserve_containers(tmp_path, enabled, master):
    psd = PSDImage.new("RGBA", (40, 40))
    styled = group(psd, "Styled")
    pixel(styled, "Base", "red", (10, 10))
    add_effect(styled, enabled=enabled, master=master)
    source = tmp_path / "disabled.psd"
    psd.save(source)
    root = export_psd(source, tmp_path / "out")
    container = root["children"][0]
    assert container["type"] == "container"
    assert container["children"][0]["asset"] == "assets/Styled/Base.png"


def test_only_styled_group_is_flattened_and_hash_still_wins(tmp_path):
    psd = PSDImage.new("RGBA", (120, 100))
    panel = group(psd, "Panel")
    styled = group(panel, "Styled")
    pixel(styled, "Base", "red", (20, 20))
    add_effect(styled)
    ordinary = group(panel, "Ordinary")
    layer = pixel(ordinary, "Styled leaf", "blue", (60, 20))
    add_effect(layer)
    ignored = group(panel, "img_Ignored#")
    add_effect(ignored)
    pixel(ignored, "Base", "lime")
    source = tmp_path / "nested.psd"
    psd.save(source)
    root = export_psd(source, tmp_path / "out")
    panel = root["children"][0]
    assert [n["type"] for n in panel["children"]] == ["image", "container"]
    assert panel["children"][1]["children"][0]["asset"] == "assets/Panel/Ordinary/Styled leaf.png"
    assert not any("Ignored" in str(p) for p in (tmp_path / "out").rglob("*"))


def test_group_style_composite_failure_remains_an_error(tmp_path, monkeypatch):
    psd = PSDImage.new("RGBA", (40, 40))
    styled = group(psd, "Styled")
    pixel(styled, "Base", "red", (10, 10))
    add_effect(styled)
    source = tmp_path / "failure.psd"
    psd.save(source)
    def fail(*args, **kwargs):
        raise ValueError("unsupported group composite")
    monkeypatch.setattr("psd2ui.exporter.composite_pil", fail)
    diagnostics = Diagnostics()
    with pytest.raises(ExportError):
        export_psd(source, tmp_path / "out", diagnostics)
    assert diagnostics.items[-1].code == "COMPOSITE_FAILED"
    assert not (tmp_path / "out/layout.json").exists()

