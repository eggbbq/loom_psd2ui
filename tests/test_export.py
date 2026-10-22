import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import BlendMode

from psd2ui.cli import main
from psd2ui.diagnostics import Diagnostics, ExportError
from psd2ui.exporter import Exporter, export_psd
from tests.fixture_factory import group, make_fixture, pixel, text


def nodes(root):
    yield root
    for child in root.get("children", []):
        yield from nodes(child)


def child(node, name):
    return next(n for n in node["children"] if n["name"] == name)


@pytest.fixture
def exported(tmp_path):
    source = make_fixture(tmp_path / "rules.psd")
    output = tmp_path / "output"
    diagnostics = Diagnostics()
    return export_psd(source, output, diagnostics), output, diagnostics


def test_pixels_hierarchy_local_coordinates_and_order(exported):
    root, output, _ = exported
    assert root["size"] == [320, 240]
    assert [n["name"] for n in root["children"]] == ["Settings", "Shop"]
    shop = child(root, "Shop")
    assert shop["position"] == [-10, -20]  # hidden child is part of actual exported bounds
    nested = child(shop, "Nested")
    assert nested["position"] == [0, 0]
    assert [n["name"] for n in nested["children"]] == ["Red", "Green", "Blue", "Hidden"]
    red = child(nested, "Red")
    assert red["position"] == [40, 70]
    assert red["asset"] == "assets/Shop/Nested/Red.png"
    assert Image.open(output / red["asset"]).getpixel((0, 0)) == (255, 0, 0, 255)


def test_exclusion_and_hidden_local_visibility(exported):
    root, output, _ = exported
    assert not any("#" in n["name"] for n in nodes(root))
    assert not child(root, "Settings")["visible"]
    assert child(child(root, "Settings"), "Background")["visible"]
    shop = child(root, "Shop")
    hidden = child(shop, "Hidden group")
    assert not hidden["visible"]
    assert child(hidden, "Locally visible")["visible"]
    assert not child(hidden, "Locally hidden")["visible"]
    for n in nodes(root):
        if n["type"] == "image":
            assert (output / n["asset"]).is_file()
            assert list(Image.open(output / n["asset"]).size) == n["size"]


def test_text_styles_and_explicit_raster_text(exported):
    root, output, _ = exported
    shop = child(root, "Shop")
    title = child(shop, "Title")
    assert title["type"] == "text" and title["text"] == "Shop\nUI"
    assert title["font"] == "Arial" and title["fontSize"] == 12
    assert title["color"] == "#FFFFFF" and title["outline"] == 0
    assert not (output / "assets/Shop/Title.png").exists()
    raster = child(shop, "text")
    assert raster["type"] == "image"
    assert Image.open(output / raster["asset"]).getchannel("A").getbbox()


def test_flatten_filter_hidden_group_opacity(exported):
    root, output, _ = exported
    baked = child(child(root, "Shop"), "Baked")
    assert baked["type"] == "image" and not baked["visible"]
    assert "opacity" not in baked and "children" not in baked
    image = Image.open(output / baked["asset"])
    assert image.size == (16, 16)
    assert image.getpixel((0, 0)) == (255, 255, 0, 128)
    assert not (output / "assets/Shop/Baked").exists()


def test_duplicate_overwrite_different_sizes_and_group_bounds(tmp_path):
    psd = PSDImage.new("RGBA", (80, 80))
    panel = group(psd, "Panel")
    pixel(panel, "same", "red", (10, 10), (10, 10))
    pixel(panel, "same", "blue", (20, 20), (30, 40))
    path = tmp_path / "duplicate.psd"
    psd.save(path)
    diagnostics = Diagnostics()
    layout = export_psd(path, tmp_path / "out", diagnostics)
    images = list(n for n in nodes(layout) if n["type"] == "image")
    assert images[0]["asset"] == images[1]["asset"]
    assert images[0]["size"] == images[1]["size"] == [30, 40]
    assert layout["children"][0]["size"] == [40, 50]
    assert Image.open(tmp_path / "out" / images[0]["asset"]).getpixel((0, 0)) == (0, 0, 255, 255)
    assert [d.code for d in diagnostics.items] == ["DUPLICATE_ASSET_PATH"]
    assert main(["export", str(path), "--output", str(tmp_path / "strict"), "--strict"]) == 0


def test_same_filename_in_separate_groups(tmp_path):
    psd = PSDImage.new("RGBA", (20, 20))
    pixel(group(psd, "A"), "icon", "red")
    pixel(group(psd, "B"), "icon", "blue")
    source = tmp_path / "two.psd"
    psd.save(source)
    diagnostics = Diagnostics()
    layout = export_psd(source, tmp_path / "out", diagnostics)
    assert len({n["asset"] for n in nodes(layout) if n["type"] == "image"}) == 2
    assert not diagnostics.items


@pytest.mark.parametrize("kind", ["unreadable", "rich", "blend"])
def test_strict_and_reports(tmp_path, kind):
    psd = PSDImage.new("RGBA", (100, 100))
    if kind == "blend":
        pixel(psd, "multiply", "red").blend_mode = BlendMode.MULTIPLY
    else:
        text(psd, readable=kind != "unreadable", rich=kind == "rich")
    source = tmp_path / "style.psd"
    psd.save(source)
    arguments = ["export", str(source), "--output", str(tmp_path / "out"), "--report", str(tmp_path / "diagnostics.json")]
    assert main(arguments) == 0
    assert main([*arguments, "--strict"]) == 1
    report = json.loads((tmp_path / "diagnostics.json").read_text())
    assert {"code", "severity", "psdPath", "message"} <= report[0].keys()
    assert report[0]["code"] == {"unreadable": "UNREADABLE_TEXT_STYLE", "rich": "UNSUPPORTED_RICH_TEXT", "blend": "UNSUPPORTED_VISUAL_EFFECT"}[kind]


def test_render_failure_does_not_publish_partial_layout(tmp_path, monkeypatch):
    source = make_fixture(tmp_path / "source.psd")
    def fail(*args, **kwargs):
        raise ValueError("simulated unsupported renderer")
    monkeypatch.setattr("psd2ui.exporter.composite_pil", fail)
    diagnostics = Diagnostics()
    with pytest.raises(ExportError):
        export_psd(source, tmp_path / "out", diagnostics)
    assert not (tmp_path / "out/layout.json").exists()
    assert diagnostics.items[-1].code == "COMPOSITE_FAILED"


def test_render_failure_preserves_previous_export(tmp_path, monkeypatch):
    source = make_fixture(tmp_path / "source.psd")
    output = tmp_path / "out"
    export_psd(source, output)
    before = {f.relative_to(output): f.read_bytes() for f in output.rglob("*") if f.is_file()}
    def fail(*args, **kwargs):
        raise RuntimeError("renderer failed")
    monkeypatch.setattr("psd2ui.exporter.composite_pil", fail)
    with pytest.raises(ExportError):
        export_psd(source, output)
    assert before == {f.relative_to(output): f.read_bytes() for f in output.rglob("*") if f.is_file()}


@pytest.mark.parametrize("target", ["source", "layout", "asset"])
def test_report_cannot_overwrite_inputs_or_export_files(tmp_path, target):
    source = make_fixture(tmp_path / "source.psd")
    original = source.read_bytes()
    report = {"source": source, "layout": tmp_path / "out/layout.json",
              "asset": tmp_path / "out/assets/Shop/Background.png"}[target]
    assert main(["export", str(source), "--output", str(tmp_path / "out"), "--report", str(report)]) == 1
    assert source.read_bytes() == original
    assert not (tmp_path / "out/layout.json").exists()


def test_render_visibility_is_restored(tmp_path):
    psd = PSDImage.open(make_fixture(tmp_path / "source.psd"))
    before = [(l.visible, l.clipping, l.opacity) for l in psd.descendants()]
    Exporter(tmp_path / "out").node(psd[1])
    assert before == [(l.visible, l.clipping, l.opacity) for l in psd.descendants()]


def test_opacity_not_applied_twice(tmp_path):
    psd = PSDImage.new("RGBA", (20, 20))
    panel = group(psd, "Panel", opacity=128)
    pixel(panel, "Image", "red", opacity=128)
    path = tmp_path / "opacity.psd"
    psd.save(path)
    layout = export_psd(path, tmp_path / "out")
    panel = layout["children"][0]
    image = panel["children"][0]
    assert panel["opacity"] == 128 / 255 and "opacity" not in image
    assert Image.open(tmp_path / "out" / image["asset"]).getpixel((0, 0))[3] == 128


def test_path_names_cannot_escape(tmp_path):
    psd = PSDImage.new("RGBA", (20, 20))
    pixel(group(psd, "../../escape"), "../CON", "red")
    path = tmp_path / "unsafe.psd"
    psd.save(path)
    layout = export_psd(path, tmp_path / "out")
    image = next(n for n in nodes(layout) if n["type"] == "image")
    assert ".." not in image["asset"]
    assert (tmp_path / "out" / image["asset"]).is_file()


def test_invalid_names_and_unreadable_psd_fail(tmp_path):
    psd = PSDImage.new("RGBA", (20, 20))
    pixel(psd, "img_", "red")
    path = tmp_path / "empty.psd"
    psd.save(path)
    assert main(["export", str(path), "--output", str(tmp_path / "out")]) == 1
    assert main(["export", str(tmp_path / "missing.psb"), "--output", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out/layout.json").exists()


def test_repeatability_real_fixture_and_both_cli_entrypoints(tmp_path):
    source = Path(__file__).parent / "fixtures/rules.psd"
    output = tmp_path / "out"
    for entry in ([sys.executable, "-m", "psd2ui"], [str(Path(sys.executable).parent / "psd2ui")]):
        result = subprocess.run([*entry, "export", str(source), "--output", str(output)], capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
        hashes = {f.relative_to(output).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in output.rglob("*") if f.is_file()}
        if "previous" in locals():
            assert previous == hashes
        previous = hashes


def test_psb_reading(tmp_path):
    psd = PSDImage.new("RGBA", (20, 20))
    pixel(psd, "PSB layer", "red")
    psd._record.header.version = 2
    path = tmp_path / "large-format.psb"
    psd.save(path)
    root = export_psd(path, tmp_path / "out")
    assert root["children"][0]["type"] == "image"


def test_real_text_stroke_and_shadow_descriptors(tmp_path):
    from psd_tools.constants import Tag
    from psd_tools.psd.descriptor import Bool, Descriptor, DescriptorBlock2, Double, Enumerated
    from psd_tools.psd.tagged_blocks import TaggedBlock
    from psd_tools.terminology import Key, Klass

    psd = PSDImage.new("RGBA", (100, 100))
    layer = text(psd, value="Effect")
    color = Descriptor(classID=Klass.RGBColor.value, items={b"Rd  ": Double(20), b"Grn ": Double(40), b"Bl  ": Double(60)})
    common = {Key.Enabled: Bool(True), b"present": Bool(True), Key.Color: color, Key.Opacity: Double(100)}
    stroke = Descriptor(classID=Klass.FrameFX.value, items={**common, Key.SizeKey: Double(3),
                        Key.PaintType: Enumerated(typeID=b"FrFl", enum=b"SClr"),
                        Key.Style: Enumerated(typeID=b"FStl", enum=b"OutF")})
    shadow = Descriptor(classID=Klass.DropShadow.value, items={**common, Key.Distance: Double(4),
                        Key.LocalLightingAngle: Double(90), Key.Blur: Double(2)})
    layer.tagged_blocks[Tag.OBJECT_BASED_EFFECTS_LAYER_INFO] = TaggedBlock(
        key=Tag.OBJECT_BASED_EFFECTS_LAYER_INFO,
        data=DescriptorBlock2(items={b"masterFXSwitch": Bool(True), b"FrFX": stroke, b"DrSh": shadow}))
    path = tmp_path / "effects.psd"
    psd.save(path)
    diagnostics = Diagnostics()
    root = export_psd(path, tmp_path / "out", diagnostics)
    node = root["children"][0]
    assert node["outline"] == 3 and node["outlineColor"] == "#14283C"
    assert node["shadow"] == [0, 4] and node["shadowColor"] == "#14283C" and node["shadowBlur"] == 2
    assert any(d.code == "UNSUPPORTED_VISUAL_EFFECT" for d in diagnostics.items)


def test_png_metadata_does_not_break_repeatability(tmp_path, monkeypatch):
    import psd2ui.exporter as module
    psd = PSDImage.new("RGBA", (20, 20))
    pixel(psd, "Image", "red")
    source = tmp_path / "metadata.psd"
    psd.save(source)
    composite = module.composite_pil
    serial = 0
    def volatile_profile(*args, **kwargs):
        nonlocal serial
        serial += 1
        image = composite(*args, **kwargs)
        image.info["icc_profile"] = b"volatile profile creation time " + str(serial).encode()
        return image
    monkeypatch.setattr(module, "composite_pil", volatile_profile)
    output = tmp_path / "out"
    export_psd(source, output)
    before = (output / "assets/Image.png").read_bytes()
    export_psd(source, output)
    assert before == (output / "assets/Image.png").read_bytes()

