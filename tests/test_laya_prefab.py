import copy
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

from psd2ui.laya_prefab import generate_prefab, write_json


def walk(node, key="_$child"):
    yield node
    for child in node.get(key, []):
        yield from walk(child, key)


@pytest.fixture
def inputs(tmp_path):
    source, project = tmp_path / "export", tmp_path / "project"
    source.mkdir()
    project.mkdir()
    main_id = str(uuid.uuid4())
    write_json(project / "src/Main.ts.meta", {"uuid": main_id})
    write_json(project / "assets/Scene.ls", {"_$ver": 1, "_$type": "Scene", "name": "Scene",
        "_$comp": [{"_$type": main_id}, {"_$type": "KeepComponent"}],
        "_$child": [{"_$id": "keep", "_$type": "Sprite", "name": "KeepNode"}]})
    Image.new("RGBA", (8, 6), "red").save(source / "icon.png")
    base = {"position": [0, 0], "size": [8, 6], "visible": True}
    layout = {**base, "version": 1, "type": "root", "name": "UI", "size": [100, 200], "children": [
        {**base, "type": "container", "name": "Panel", "position": [-20, 10], "visible": False,
         "opacity": 0.5, "children": [
            {**base, "type": "image", "name": "same", "position": [2, 3], "asset": "icon.png"},
            {**base, "type": "image", "name": "same", "position": [4, 5], "visible": False, "asset": "icon.png"},
            {**base, "type": "text", "name": "Title", "text": "标题\nUI", "font": "Arial", "fontSize": 24,
             "color": "#FFFFFF", "align": "right", "outline": 2, "outlineColor": "#000000",
             "shadow": [-1, 2], "shadowColor": "#010203", "shadowBlur": 3, "opacity": 0.7},
            {**base, "type": "container", "name": "Empty", "size": [0, 0], "children": []},
        ]},
    ]}
    write_json(source / "layout.json", layout)
    return source, project, layout


def test_native_hierarchy_text_and_texture_refs(inputs):
    source, project, layout = inputs
    result = generate_prefab(source / "layout.json", project)
    assert Path(result["prefab"]).name == "UI.lh"
    prefab = json.loads(Path(result["prefab"]).read_text())
    assert result["textures"] == 1 and result["nodes"] == 6
    assert prefab["_$ver"] == 1 and prefab["_$type"] == "GWidget"
    panel = prefab["_$child"][0]
    assert panel["_$type"] == "GWidget"
    assert (panel["x"], panel["y"], panel["visible"], panel["alpha"]) == (-20, 10, False, 0.5)
    images = panel["_$child"][:2]
    assert images[0]["src"] == images[1]["src"]
    assert all(n["_$type"] == "GImage" and n["autoSize"] is False and "skin" not in n for n in images)
    assert images[0]["_$id"] != images[1]["_$id"]
    assert not images[1]["visible"]
    assert "alpha" not in images[0]
    texture = project / "assets/PSD2UI/UI/icon.png"
    meta = json.loads(texture.with_suffix(".png.meta").read_text())
    assert images[0]["src"] == "res://" + meta["uuid"]
    assert texture.read_bytes() == (source / "icon.png").read_bytes()
    text = panel["_$child"][2]
    assert text["_$type"] == "GTextField" and text["text"] == "标题\nUI"
    assert (text["fontSize"], text["stroke"], text["strokeColor"]) == (24, 2, "#000000")
    assert (text["shadowOffsetX"], text["shadowOffsetY"], text["shadowBlur"], text["alpha"]) == (-1, 2, 3, 0.7)
    assert not any("zOrder" in n or "layoutUrl" in n for n in walk(prefab))
    assert panel["_$child"][3]["_$type"] == "GWidget"
    assert len({n["_$id"] for n in walk(prefab)}) == result["nodes"]


def test_scene_contains_static_prefab_and_preserves_other_nodes(inputs):
    source, project, _ = inputs
    for _ in range(2):
        result = generate_prefab(source / "layout.json", project, scene="assets/Scene.ls")
    scene = json.loads((project / "assets/Scene.ls").read_text())
    assert scene["_$comp"] == [{"_$type": "KeepComponent"}]
    assert scene["_$child"][0]["name"] == "KeepNode"
    assert len(scene["_$child"]) == 2
    assert scene["_$child"][1]["_$prefab"] == result["uuid"]
    assert [scene["width"], scene["height"]] == [100, 200]


def test_scene_instance_overrides_are_preserved(inputs):
    source, project, _ = inputs
    generate_prefab(source / "layout.json", project, scene="assets/Scene.ls")
    path = project / "assets/Scene.ls"
    scene = json.loads(path.read_text())
    instance = scene["_$child"][-1]
    instance.update(x=50, visible=False, **{"_$child": [{"_$id": "custom", "_$type": "GLoader", "name": "Custom"}]})
    write_json(path, scene)
    generate_prefab(source / "layout.json", project, scene="assets/Scene.ls")
    assert json.loads(path.read_text())["_$child"][-1] == instance


def test_stable_ids_and_existing_meta_are_preserved(inputs):
    source, project, _ = inputs
    generate_prefab(source / "layout.json", project)
    meta_path = project / "assets/PSD2UI/UI/icon.png.meta"
    meta = json.loads(meta_path.read_text())
    meta["importer"]["filterMode"] = 0
    meta["uuid"] = str(uuid.uuid4())
    write_json(meta_path, meta)
    generate_prefab(source / "layout.json", project)
    before = {str(f): f.read_bytes() for f in project.rglob("*") if f.is_file()}
    generate_prefab(source / "layout.json", project)
    assert before == {str(f): f.read_bytes() for f in project.rglob("*") if f.is_file()}
    assert json.loads(meta_path.read_text()) == meta


@pytest.mark.parametrize("failure", ["missing", "size", "version", "traversal", "nan", "shadow"])
def test_invalid_input_preserves_previous_prefab(inputs, failure):
    source, project, layout = inputs
    generate_prefab(source / "layout.json", project)
    before = {str(f): f.read_bytes() for f in project.rglob("*") if f.is_file()}
    modified = copy.deepcopy(layout)
    if failure == "missing":
        (source / "icon.png").unlink()
    elif failure == "size":
        modified["children"][0]["children"][0]["size"] = [9, 6]
    elif failure == "version":
        modified["version"] = 2
    elif failure == "traversal":
        modified["children"][0]["children"][0]["asset"] = "../outside.png"
    elif failure == "nan":
        modified["position"] = [float("nan"), 0]
    else:
        modified["children"][0]["children"][2]["shadow"] = []
    (source / "layout.json").write_text(json.dumps(modified))
    with pytest.raises((ValueError, OSError, IndexError)):
        generate_prefab(source / "layout.json", project)
    assert before == {str(f): f.read_bytes() for f in project.rglob("*") if f.is_file()}


@pytest.mark.parametrize("output", ["../outside.lh", "bin/not-an-asset.lh", "assets/bad.json"])
def test_prefab_must_stay_inside_assets(inputs, output):
    source, project, _ = inputs
    with pytest.raises(ValueError):
        generate_prefab(source / "layout.json", project, output)


def test_script_entrypoint(inputs):
    source, project, _ = inputs
    script = Path(__file__).resolve().parents[1] / "scripts/generate_laya_prefab.py"
    result = subprocess.run([sys.executable, str(script), str(source / "layout.json"),
                             "--project", str(project), "--output", "assets/UI.lh"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["textures"] == 1
    assert (project / "assets/UI.lh").exists()

