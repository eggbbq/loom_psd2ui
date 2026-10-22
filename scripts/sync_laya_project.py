"""Regenerate the native prefab from the latest PSD export and bind the scene."""
import argparse
import json
from pathlib import Path

from psd2ui.laya_prefab import generate_prefab


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-output", type=Path, default=root / "out/test")
    args = parser.parse_args()
    source = args.source_output.resolve()
    project = root / "laya-project"
    if not (project / "PSD2UIDemo.laya").is_file():
        parser.error("Native project is missing: laya-project/PSD2UIDemo.laya")
    result = generate_prefab(source / "layout.json", project, scene="assets/Scene.ls")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

