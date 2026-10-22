"""Read layout.json and generate an editable native LayaAir 3.4.1 prefab."""
import argparse
import json
from pathlib import Path

from psd2ui.laya_prefab import generate_prefab


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path, nargs="?", default=root / "out/test/layout.json")
    parser.add_argument("--project", type=Path, default=root / "laya-project")
    parser.add_argument("--output", default="assets/PSD2UI/test.lh", help="Prefab path relative to the project")
    parser.add_argument("--scene", help="Optional existing .ls to place a prefab instance in (project-relative)")
    args = parser.parse_args()
    try:
        result = generate_prefab(args.layout, args.project, args.output, args.scene)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Prefab generation failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

