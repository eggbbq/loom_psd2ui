"""Generate a portable .lh and .meta files in an exported PSD directory."""
import argparse
import json
from pathlib import Path

from psd2ui.laya_prefab import generate_asset_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path, help="Exported layout.json")
    args = parser.parse_args()
    try:
        result = generate_asset_bundle(args.layout)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Bundle generation failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
