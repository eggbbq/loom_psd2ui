import json

import pytest

from psd2ui.laya_prefab import write_json
from scripts.sync_laya_project import sync_project


def test_switching_psd_updates_design_canvas_and_preserves_user_settings(tmp_path):
    source, project = tmp_path / "export", tmp_path / "project"
    settings_path = project / "settings/PlayerSettings.json"
    settings = {"resolution": {"designWidth": 750, "designHeight": 1624,
                "scaleMode": "showall", "alignH": "center", "alignV": "middle"},
                "modules": {"laya.ui": True}, "addons": {"laya.ui": "ui2"}, "splash": {"fit": "center"}}
    write_json(settings_path, settings)
    write_json(project / "assets/Scene.ls", {"_$ver": 1, "_$type": "Scene", "name": "Scene",
               "_$child": [{"_$type": "GLoader", "name": "Keep"}]})
    layout = dict(version=1, type="root", name="UI", position=[0, 0],
                  size=[750, 1624], visible=True, children=[])
    for size in ([720, 1280], [750, 1624]):
        layout["name"] = f"UI{size[0]}"
        layout["size"] = size
        write_json(source / "layout.json", layout)
        result = sync_project(source, project)
        after = json.loads(settings_path.read_text())
        assert after["resolution"].pop("designWidth") == size[0]
        assert after["resolution"].pop("designHeight") == size[1]
        expected = json.loads(json.dumps(settings))
        expected["resolution"].pop("designWidth")
        expected["resolution"].pop("designHeight")
        assert after == expected
        assert result["canvas"] == size
        assert result["prefab"].endswith(f"/assets/psd2ui/{layout['name']}/{layout['name']}.lh")
        scene = json.loads((project / "assets/Scene.ls").read_text())
        assert [scene["width"], scene["height"]] == size
        assert scene["_$child"][0]["name"] == "Keep"
        assert len(scene["_$child"]) == 2


def test_invalid_layout_does_not_overwrite_resolution(tmp_path):
    source, project = tmp_path / "export", tmp_path / "project"
    settings_path = project / "settings/PlayerSettings.json"
    write_json(settings_path, {"resolution": {"designWidth": 750, "designHeight": 1624}})
    original = settings_path.read_bytes()
    write_json(source / "layout.json", dict(version=1, type="root", name="UI", position=[0, 0],
               size=[0, 0], visible=True, children=[]))
    with pytest.raises(ValueError, match="canvas"):
        sync_project(source, project)
    assert settings_path.read_bytes() == original
