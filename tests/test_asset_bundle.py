import json
from pathlib import Path

import pytest
from PIL import Image
from psd_tools import PSDImage

from psd2ui.cli import main
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_asset_bundle, generate_prefab, write_json
from tests.fixture_factory import group, pixel, text


def walk(node, key="children"):
    yield node
    for child in node.get(key, []):
        yield from walk(child, key)


def test_flat_export_bundle_preserves_psd_folders_and_uses_single_set_of_pngs(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    shop = group(psd, "Shop")
    pixel(shop, "img_Background", "red", (10, 20), (30, 20))
    button = group(shop, "btn_Buy")
    pixel(button, "img_Icon", "blue", (15, 25), (10, 10))
    text(button, "Caption", "Buy", (20, 30))
    source = tmp_path / "商城_给程序.psd"
    psd.save(source)
    output = tmp_path / source.stem
    assert main(["export", str(source), "--output", str(output), "--flat-assets"]) == 0
    layout = json.loads((output / "layout.json").read_text())
    assets = {n["asset"] for n in walk(layout) if n["type"] == "image"}
    assert assets == {"Shop/Background.png", "Shop/Buy/Icon.png"}
    before = {asset: (output / asset).read_bytes() for asset in assets}
    generated = generate_asset_bundle(output / "layout.json")
    assert Path(generated["prefab"]) == output / "商城_给程序.lh"
    assert generated["textures"] == 2
    assert not (output / "assets").exists()
    assert not (output / "商城_给程序").exists()
    assert {p.relative_to(output).as_posix() for p in output.rglob("*.png")} == assets
    assert before == {asset: (output / asset).read_bytes() for asset in assets}
    uuids = {json.loads((output / (asset + ".meta")).read_text())["uuid"] for asset in assets}
    prefab = json.loads(Path(generated["prefab"]).read_text())
    assert {n["src"][6:] for n in walk(prefab, "_$child") if "src" in n} == uuids
    assert any(n["_$type"] == "GButton" for n in walk(prefab, "_$child"))
    assert any(n["_$type"] == "GTextField" and n["text"] == "Buy" for n in walk(prefab, "_$child"))
    # Repeat generation preserves UUIDs and custom importer settings.
    meta_path = output / "Shop/Background.png.meta"
    meta = json.loads(meta_path.read_text())
    meta["importer"]["generateMipmap"] = True
    write_json(meta_path, meta)
    assert generate_asset_bundle(output / "layout.json")["uuid"] == generated["uuid"]
    assert json.loads(meta_path.read_text()) == meta
    # Explicit project import keeps exactly the same relative PNG tree.
    project = tmp_path / "project"
    project.mkdir()
    imported = generate_prefab(output / "layout.json", project,
                              output="assets/psd2ui/商城_给程序/商城_给程序.lh",
                              preserve_resource_paths=True)
    native_dir = Path(imported["prefab"]).parent
    assert {p.relative_to(native_dir).as_posix() for p in native_dir.rglob("*.png")} == assets


def test_different_psd_bundles_have_distinct_resource_uuids(tmp_path):
    ids = []
    for name in ("First", "Second"):
        source = tmp_path / (name + ".psd")
        psd = PSDImage.new("RGBA", (40, 40))
        pixel(psd, "Picture", "red")
        psd.save(source)
        output = tmp_path / name
        export_psd(source, output, flat_assets=True)
        generated = generate_asset_bundle(output / "layout.json")
        ids.append((generated["uuid"], json.loads((output / "Picture.png.meta").read_text())["uuid"]))
    assert ids[0][0] != ids[1][0] and ids[0][1] != ids[1][1]


def test_missing_png_leaves_previous_bundle_untouched(tmp_path):
    source = tmp_path / "source.psd"
    psd = PSDImage.new("RGBA", (40, 40))
    pixel(psd, "Picture", "red")
    psd.save(source)
    output = tmp_path / "source"
    export_psd(source, output, flat_assets=True)
    generated = generate_asset_bundle(output / "layout.json")
    prefab = Path(generated["prefab"])
    before = prefab.read_bytes()
    (output / "Picture.png").unlink()
    with pytest.raises(FileNotFoundError):
        generate_asset_bundle(output / "layout.json")
    assert prefab.read_bytes() == before


def test_flat_report_cannot_overwrite_png_asset(tmp_path):
    source = tmp_path / "source.psd"
    psd = PSDImage.new("RGBA", (40, 40))
    pixel(psd, "Picture", "red")
    psd.save(source)
    output = tmp_path / "source"
    report = output / "Picture.png"
    assert main(["export", str(source), "--output", str(output), "--flat-assets", "--report", str(report)]) == 1
    assert not report.exists()
    assert not (output / "layout.json").exists()


def test_flat_group_cannot_shadow_layout_json(tmp_path):
    from psd2ui.diagnostics import ExportError
    source = tmp_path / "source.psd"
    psd = PSDImage.new("RGBA", (40, 40))
    pixel(group(psd, "layout.json"), "Picture", "red")
    psd.save(source)
    with pytest.raises(ExportError, match="layout.json"):
        export_psd(source, tmp_path / "out", flat_assets=True)
