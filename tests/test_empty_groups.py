import json
from pathlib import Path

import pytest
from PIL import Image
from psd_tools import PSDImage

from psd2ui.diagnostics import Diagnostics
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel, text
from tests.test_group_effects import add_effect


@pytest.mark.parametrize("name", ["Empty", "img_Empty", "icon_Empty", "pnl_Empty", "btn_Empty", "vbox_Empty", "img_"])
@pytest.mark.parametrize("flat", [True, False])
def test_empty_groups_do_not_create_nodes_assets_or_directories(tmp_path, name, flat):
    psd = PSDImage.new("RGBA", (100, 100))
    group(psd, name)
    source = tmp_path / "empty.psd"
    psd.save(source)
    output = tmp_path / "out"
    diagnostics = Diagnostics()
    root = export_psd(source, output, diagnostics, flat_assets=flat)
    assert root["children"] == []
    assert not diagnostics.items
    assert list(output.iterdir()) == [output / "layout.json"]
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(output / "layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())
    assert not native.get("_$child")


def test_recursively_empty_and_filtered_groups_are_omitted_but_live_siblings_keep_bounds(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    group(group(group(psd, "EmptyRoot"), "EmptyChild"), "EmptyGrandchild")
    filtered = group(psd, "Filtered")
    pixel(filtered, "Skip#", "blue")
    live = group(psd, "Live")
    group(live, "EmptySibling")
    nested = group(live, "Content")
    pixel(nested, "Picture", "red", (20, 30), (16, 10), visible=False)
    source = tmp_path / "nested.psd"
    psd.save(source)
    output = tmp_path / "out"
    root = export_psd(source, output, flat_assets=True)
    assert [n["name"] for n in root["children"]] == ["Live"]
    live = root["children"][0]
    assert live["position"] == [20, 30] and live["size"] == [16, 10]
    assert [n["name"] for n in live["children"]] == ["Content"]
    assert not live["children"][0]["children"][0]["visible"]
    assert {p.relative_to(output).as_posix() for p in output.rglob("*")} == {
        "layout.json", "Live", "Live/Content", "Live/Content/Picture.png"}


def test_empty_styled_group_is_skipped_without_rendering_or_effect_diagnostics(tmp_path, monkeypatch):
    psd = PSDImage.new("RGBA", (100, 100))
    add_effect(group(psd, "Styled"))
    source = tmp_path / "styled.psd"
    # psd-tools cannot synthesize the merged preview for a 0x0 styled group.
    # Supply only that preview; the PSD retains the actual empty group/style.
    with monkeypatch.context() as preview:
        preview.setattr(psd, "composite", lambda **kwargs: Image.new("RGBA", psd.size))
        psd.save(source)
    monkeypatch.setattr("psd2ui.exporter.composite_pil", lambda *a, **k: pytest.fail("Empty group must not render"))
    diagnostics = Diagnostics()
    assert export_psd(source, tmp_path / "out", diagnostics)["children"] == []
    assert not diagnostics.items


def test_text_only_and_hidden_nonempty_groups_are_preserved(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    hidden = group(psd, "Hidden", visible=False)
    text(hidden, "txt_Caption", "Hello", (5, 10))
    source = tmp_path / "text.psd"
    psd.save(source)
    output = tmp_path / "out"
    root = export_psd(source, output, flat_assets=True)
    assert root["children"][0]["name"] == "Hidden"
    assert not root["children"][0]["visible"]
    assert root["children"][0]["children"][0]["type"] == "text"
    assert (output / "Hidden").is_dir()


def test_empty_styled_child_is_excluded_from_flattened_group_rendering(tmp_path, monkeypatch):
    psd = PSDImage.new("RGBA", (100, 100))
    parent = group(psd, "img_Panel")
    pixel(parent, "Content", "red", (10, 20), (16, 12))
    add_effect(group(parent, "EmptyStyled"))
    source = tmp_path / "flattened.psd"
    with monkeypatch.context() as preview:
        preview.setattr(psd, "composite", lambda **kwargs: Image.new("RGBA", psd.size))
        psd.save(source)
    diagnostics = Diagnostics()
    output = tmp_path / "out"
    node = export_psd(source, output, diagnostics)["children"][0]
    assert node["type"] == "image" and node["position"] == [10, 20] and node["size"] == [16, 12]
    assert not diagnostics.items
    with Image.open(output / node["asset"]) as png:
        assert png.getpixel((0, 0)) == (255, 0, 0, 255)
