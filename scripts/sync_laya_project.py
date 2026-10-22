"""Regenerate the native prefab from the latest PSD export and bind the scene."""
import argparse
import json
from pathlib import Path

from psd2ui.laya_prefab import bundle_name, generate_prefab, node_id, validate_layout, write_json


def sync_project(source, project):
    """Keep the demo stage, scene and prefab on the PSD's coordinate canvas."""
    source, project = Path(source), Path(project)
    layout_path = source / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    validate_layout(layout)
    width, height = layout["size"]
    if width <= 0 or height <= 0:
        raise ValueError("PSD canvas dimensions must be positive")
    name = bundle_name(layout)
    settings_path = project / "settings/PlayerSettings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    resolution = settings.setdefault("resolution", {})
    if not isinstance(resolution, dict):
        raise ValueError("PlayerSettings.resolution must be an object")
    result = generate_prefab(layout_path, project,
                            output=f"assets/psd2ui/{name}/{name}.lh", scene="assets/Scene.ls",
                            preserve_resource_paths=True,
                            scene_instance_id=node_id(("instance", "assets/PSD2UI/test.lh")))
    resolution.update(designWidth=width, designHeight=height)
    write_json(settings_path, settings)
    return {**result, "canvas": [width, height]}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-output", type=Path, default=root / "out/test")
    args = parser.parse_args()
    source = args.source_output.resolve()
    project = root / "laya-project"
    if not (project / "PSD2UIDemo.laya").is_file():
        parser.error("Native project is missing: laya-project/PSD2UIDemo.laya")
    result = sync_project(source, project)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

