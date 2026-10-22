import json
from pathlib import Path

import pytest
from psd_tools import PSDImage

from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel, text


@pytest.mark.parametrize("alias,component", [
    ("背景", "GImage"), ("按钮", "GButton"), ("标题", "GTextField"),
    ("边框", "GImage"), ("图标", "GLoader"), ("图片", "GImage"),
    ("花边", "GImage"), ("底板", "GImage"),
])
@pytest.mark.parametrize("suffix", ["", "_Element"])
def test_chinese_aliases_from_real_psd_to_native_prefab(tmp_path, alias, component, suffix):
    psd = PSDImage.new("RGBA", (160, 120))
    if component == "GTextField":
        text(psd, alias + suffix, "Heading", (10, 10))
    else:
        parent = group(psd, alias + suffix)
        pixel(parent, "Visual", "red", (10, 10), (100, 80))
        text(parent, "Caption", "UI", (20, 20))
    source = tmp_path / "chinese.psd"
    psd.save(source)
    output = tmp_path / "out"
    node = export_psd(source, output)["children"][0]
    assert node["component"] == component
    assert node["name"] == ("Element" if suffix else alias)
    if component in ("GImage", "GLoader"):
        assert node["type"] == "image" and "children" not in node
        assert list(output.rglob("*.png")) == [output / node["asset"]]
    elif component == "GButton":
        assert node["type"] == "container" and len(node["children"]) == 2
        assert node["children"][1]["name"] == "title"
    else:
        assert node["type"] == "text" and node["text"] == "Heading"
        assert not list(output.rglob("*.png"))
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(output / "layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())["_$child"][0]
    assert native["_$type"] == component and native["name"] == node["name"]
    if component in ("GImage", "GLoader"):
        assert "_$child" not in native and native["src"].startswith("res://")
