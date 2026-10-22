import json
from pathlib import Path

import pytest
from psd_tools import PSDImage

from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from psd2ui.naming import is_variable_name
from tests.fixture_factory import group, pixel, text


@pytest.mark.parametrize("raw,expected", [
    ("Caption", "text"), ("Lv 10", "text"), ("123", "text"),
    ("txt_player_name", "player_name"), ("title_Heading", "Heading"),
    ("input_account", "account"), ("text", "text"), ("title", "title"),
    ("txt_123", "text"), ("txt_default", "text"), ("txt_bad-name", "text"),
    ("txt_a/b", "text"), ("txt_ ", "text"), ("txt_Name ", "text"),
    ("txt_变量", "变量"), ("txt_$amount", "$amount"),
])
def test_text_names_use_type_match_and_original_identifier(tmp_path, raw, expected):
    psd = PSDImage.new("RGBA", (200, 120))
    text(psd, raw, "Displayed text")
    source = tmp_path / "names.psd"
    psd.save(source)
    node = export_psd(source, tmp_path / "out")["children"][0]
    assert node["name"] == expected and node["type"] == "text"
    assert node["text"] == "Displayed text"
    assert PSDImage.open(source)[0].name == raw


@pytest.mark.parametrize("parent_name,expected", [
    ("btn_Submit", "title"), ("Button", "title"),
    ("progressbar_Health", "title"), ("ProgressBar", "title"),
    ("bar_Health", "title"), ("bar", "title"),
    ("box_Panel", "text"),
])
def test_button_and_progressbar_title_context_survives_nested_groups(tmp_path, parent_name, expected):
    psd = PSDImage.new("RGBA", (200, 120))
    parent = group(psd, parent_name)
    nested = group(parent, "Content")
    text(nested, "Caption", "First")
    text(nested, "txt_123", "Second")
    text(nested, "txt_status", "Kept")
    source = tmp_path / "context.psd"
    psd.save(source)
    node = export_psd(source, tmp_path / "out")["children"][0]["children"][0]
    assert [n["name"] for n in node["children"]] == [expected, expected, "status"]
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(tmp_path / "out/layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())["_$child"][0]["_$child"][0]["_$child"]
    assert [n["name"] for n in native] == [expected, expected, "status"]
    assert len({n["_$id"] for n in native}) == 3
    assert all(n["_$type"] == "GTextField" for n in native)


def test_text_control_wrapper_uses_title_for_its_fallback_visual(tmp_path):
    psd = PSDImage.new("RGBA", (200, 120))
    text(psd, "btn_123", "Click")
    source = tmp_path / "text-button.psd"
    psd.save(source)
    node = export_psd(source, tmp_path / "out")["children"][0]
    assert node["component"] == "GButton" and node["name"] == "text"
    assert node["children"][0]["name"] == "title" and node["children"][0]["text"] == "Click"


def test_explicit_raster_text_name_falls_back_but_pixel_layer_name_is_preserved(tmp_path):
    psd = PSDImage.new("RGBA", (200, 120))
    parent = group(psd, "progressbar_Health")
    text(parent, "img_Baked caption", "Baked")
    pixel(parent, "Picture with spaces", "red")
    source = tmp_path / "raster.psd"
    psd.save(source)
    children = export_psd(source, tmp_path / "out")["children"][0]["children"]
    assert children[0]["name"] == "title" and children[0]["type"] == "image"
    assert children[0]["asset"].endswith("/title.png")
    assert children[1]["name"] == "Picture with spaces"


@pytest.mark.parametrize("name,valid", [
    ("_label", True), ("$label", True), ("标签", True), ("item2", True),
    ("class", False), ("default", False), ("return", False),
    ("2item", False), ("item-name", False), ("item name", False),
])
def test_program_variable_names(name, valid):
    assert is_variable_name(name) is valid
