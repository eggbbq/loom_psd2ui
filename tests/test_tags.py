import json
from pathlib import Path

import pytest
from psd_tools import PSDImage

from psd2ui.exporter import export_psd
from psd2ui.diagnostics import Diagnostics
from psd2ui.laya_prefab import generate_prefab, write_json
from tests.fixture_factory import group, make_tag_fixture, pixel, text
from tests.test_group_effects import add_effect


def test_container_tags_survive_psd_export_and_native_prefab(tmp_path):
    layout_path = tmp_path / "out/layout.json"
    layout = export_psd(make_tag_fixture(tmp_path / "tags.psd"), layout_path.parent)
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(layout_path, project)
    prefab = json.loads(Path(result["prefab"]).read_text())
    assert [n["name"] for n in layout["children"]] == ["Row", "Column", "Window"]
    assert [n["component"] for n in layout["children"]] == ["GBox", "GBox", "GPanel"]
    assert [n["_$type"] for n in prefab["_$child"]] == ["GBox", "GBox", "GPanel"]
    assert [n.get("layout") for n in layout["children"]] == ["horizontal", "vertical", None]
    assert prefab["_$child"][0]["layout"] == {"type": 2, "columnGap": 15}
    assert prefab["_$child"][1]["layout"] == {"type": 1, "rowGap": 12}
    for source, native in zip(layout["children"], prefab["_$child"]):
        assert source["type"] == "container"
        assert [n["name"] for n in native["_$child"]] == ["text", "text"]
        assert [native["x"], native["y"]] == source["position"]
        assert [native["width"], native["height"]] == source["size"]


def test_image_prefix_replaces_old_markers_and_hash_wins(tmp_path):
    psd = PSDImage.new("RGBA", (160, 120))
    for name in ("img_Baked", "[img]Legacy", "[image]Legacy", "Middleimg_", "IMG_Upper"):
        pixel(group(psd, name), "Child", "red", (10, 10))
    text(psd, "img_Raster text", "UI", (30, 40))
    pixel(group(psd, "img_Excluded#"), "Child", "red")
    source = tmp_path / "image-tags.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output)
    nodes = layout["children"]
    assert [n["type"] for n in nodes] == ["image", "container", "container", "container", "image", "image"]
    assert nodes[0]["name"] == "Baked" and nodes[0]["asset"] == "assets/Baked.png"
    assert nodes[-1]["name"] == "text"
    assert not (output / "assets/Baked/Child.png").exists()
    assert nodes[1]["name"] == "[img]Legacy" and nodes[2]["name"] == "[image]Legacy"


def test_nested_tags_keep_asset_paths_visibility_and_opacity(tmp_path):
    psd = PSDImage.new("RGBA", (40, 40))
    row = group(psd, "hbox_Row", visible=False, opacity=128)
    column = group(row, "vhox_Column")
    panel = group(column, "panel_Window")
    pixel(panel, "img_Icon", "red", (10, 10))
    source = tmp_path / "nested.psd"
    psd.save(source)
    output = tmp_path / "out"
    row = export_psd(source, output)["children"][0]
    assert not row["visible"] and row["opacity"] == 128 / 255
    column = row["children"][0]
    panel = column["children"][0]
    assert [n["component"] for n in (row, column, panel)] == ["GBox", "GBox", "GPanel"]
    image = panel["children"][0]
    assert image["asset"] == "assets/Row/Column/Window/Icon.png"
    assert (output / image["asset"]).is_file()


@pytest.mark.parametrize("prefix", ["hbox_", "vhox_", "panel_"])
def test_group_effects_take_priority_over_container_tags(tmp_path, prefix):
    psd = PSDImage.new("RGBA", (40, 40))
    parent = group(psd, prefix + "Styled")
    pixel(parent, "Child", "red", (10, 10))
    add_effect(parent)
    source = tmp_path / "styled.psd"
    psd.save(source)
    node = export_psd(source, tmp_path / "out")["children"][0]
    assert node["name"] == "Styled" and node["type"] == "container"
    assert node["component"] in ("GBox", "GPanel")
    assert len(node["children"]) == 1
    assert node["children"][0]["type"] == "image"
    assert "children" not in node["children"][0]


@pytest.mark.parametrize("component", ["Unknown", "Sprite", None, {}, ["HBox"]])
def test_invalid_container_component_does_not_overwrite_prefab(tmp_path, component):
    layout_path = tmp_path / "out/layout.json"
    layout = export_psd(make_tag_fixture(tmp_path / "tags.psd"), layout_path.parent)
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(layout_path, project)
    destination = Path(result["prefab"])
    before = destination.read_bytes()
    layout["children"][0]["component"] = component
    write_json(layout_path, layout)
    with pytest.raises(ValueError, match="Invalid New UI component"):
        generate_prefab(layout_path, project)
    assert destination.read_bytes() == before


def test_all_new_ui_aliases_and_generic_types(tmp_path):
    layout_path = tmp_path / "out/layout.json"
    layout = export_psd(make_tag_fixture(tmp_path / "tags.psd", extended=True), layout_path.parent)
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(layout_path, project)
    prefab = json.loads(Path(result["prefab"]).read_text())
    native = {n["name"]: n for n in prefab["_$child"]}
    for name, expected in {"ShortPanel": "GPanel", "Button": "GButton", "ShortButton": "GButton",
                           "List": "GList", "Progress": "GProgressBar", "ShortProgress": "GProgressBar", "Combo": "GComboBox",
                           "Slider": "GSlider", "Loader": "GLoader", "Icon": "GLoader", "ShortIcon": "GLoader",
                           "Generic": "GLabel", "Exact": "GButton", "NativeImage": "GImage",
                           "Leaf": "GButton", "Caption": "GTextField", "Heading": "GTextField", "Account": "GTextInput"}.items():
        assert native[name]["_$type"] == expected
    for name in ("Loader", "Icon", "ShortIcon"):
        assert native[name]["src"].startswith("res://") and native[name]["fitMode"] == 1
        assert "_$child" not in native[name]
    assert native["NativeImage"]["autoSize"] is False
    assert native["Leaf"]["_$child"][0]["_$type"] == "GImage"
    assert native["Leaf"]["_$child"][0]["src"].startswith("res://")
    assert native["Button"]["_$child"][0]["_$type"] == "GTextField"


def test_unknown_prefix_stays_literal_and_explicit_text_is_editable(tmp_path):
    psd = PSDImage.new("RGBA", (160, 120))
    pixel(group(psd, "unknown_Name"), "Child", "red")
    text(psd, "text_Title", "UI", (30, 40))
    source = tmp_path / "unknown.psd"
    psd.save(source)
    layout = export_psd(source, tmp_path / "out")
    assert layout["children"][0]["name"] == "unknown_Name"
    assert "component" not in layout["children"][0]
    assert layout["children"][1]["name"] == "Title"
    assert layout["children"][1]["type"] == "text"
    assert layout["children"][1]["component"] == "GTextField"


@pytest.mark.parametrize("prefix,expected", [("txt_", "GTextField"), ("text_", "GTextField"), ("title_", "GTextField"),
                                               ("input_", "GTextInput")])
def test_text_aliases_use_editable_new_ui_text(tmp_path, prefix, expected):
    psd = PSDImage.new("RGBA", (160, 120))
    text(psd, prefix + "player_name", "UI", (30, 40))
    source = tmp_path / "text-alias.psd"
    psd.save(source)
    node = export_psd(source, tmp_path / "out")["children"][0]
    assert node["name"] == "player_name" and node["type"] == "text"
    assert node["component"] == expected and node["text"] == "UI"
    assert not list((tmp_path / "out").rglob("*.png"))
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(tmp_path / "out/layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())["_$child"][0]
    assert native["_$type"] == expected and native["text"] == "UI"
    if expected == "GTextInput":
        assert "overflow" not in native and "wordWrap" not in native


def test_full_names_without_underscore_match_types_and_preserve_names(tmp_path):
    psd = PSDImage.new("RGBA", (160, 120))
    pixel(group(psd, "Button"), "Visual", "red", (10, 10))
    pixel(group(psd, "icon"), "Visual", "red", (10, 10))
    text(psd, "txt", "UI", (30, 40))
    text(psd, "UnknownCaption", "Fallback", (30, 40))
    source = tmp_path / "full-names.psd"
    psd.save(source)
    layout = export_psd(source, tmp_path / "out")
    assert [n["name"] for n in layout["children"]] == ["Button", "icon", "txt", "text"]
    assert [n.get("component") for n in layout["children"]] == ["GButton", "GLoader", "GTextField", None]
    assert layout["children"][-1]["type"] == "text"
    assert layout["children"][-1]["text"] == "Fallback"
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(tmp_path / "out/layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())
    assert [n["_$type"] for n in native["_$child"]] == ["GButton", "GLoader", "GTextField", "GTextField"]


@pytest.mark.parametrize("name,expected_name,component", [
    ("icon", "icon", "GLoader"), ("icon_头像", "头像", "GLoader"),
    ("ico", "ico", "GLoader"), ("ico_头像", "头像", "GLoader"),
    ("ICO_头像", "头像", "GLoader"),
    ("image", "image", "GImage"), ("image_背景", "背景", "GImage"),
    ("img_背景", "背景", "GImage"),
])
def test_image_groups_export_one_png_without_any_internal_nodes(tmp_path, name, expected_name, component):
    psd = PSDImage.new("RGBA", (160, 120))
    parent = group(psd, name, visible=False)
    pixel(parent, "Background", "red", (10, 10), (100, 80))
    text(parent, "Caption", "Baked", (20, 20))
    nested = group(parent, "Nested")
    pixel(nested, "Detail", "blue", (20, 20))
    pixel(parent, "#Excluded", "green", (10, 10), (100, 80))
    source = tmp_path / "whole-image.psd"
    psd.save(source)
    output = tmp_path / "out"
    layout = export_psd(source, output, Diagnostics())
    node = layout["children"][0]
    assert node["type"] == "image" and node["component"] == component
    assert node["name"] == expected_name and not node["visible"]
    assert "children" not in node
    assert list(output.rglob("*.png")) == [output / node["asset"]]
    assert not (output / "assets" / expected_name).exists()
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(output / "layout.json", project)
    assert result["nodes"] == 2 and result["images"] == 1 and result["texts"] == 0
    native = json.loads(Path(result["prefab"]).read_text())["_$child"][0]
    assert native["_$type"] == component and "_$child" not in native
