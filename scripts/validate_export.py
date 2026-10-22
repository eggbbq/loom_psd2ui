"""Run the user's real PSD twice, check every asset, strict status and determinism."""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from psd_tools import PSDImage

from psd2ui.diagnostics import Diagnostics
from psd2ui.deduplication import similarity_threshold
from psd2ui.exporter import export_psd
from psd2ui.naming import tag_component


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path("test.psd"))
    parser.add_argument("--output", type=Path, default=Path("out/test"))
    parser.add_argument("--validation", type=Path, default=Path("out/validation"))
    parser.add_argument("--dedupe-images", type=similarity_threshold)
    args = parser.parse_args()
    args.validation.mkdir(parents=True, exist_ok=True)
    original = sha(args.source)
    diagnostics = Diagnostics()
    layout = export_psd(args.source, args.output, diagnostics, dedupe_images=args.dedupe_images)
    all_nodes = list(walk(layout))
    assets = {n["asset"] for n in all_nodes if n["type"] == "image"}
    before = {path: sha(args.output / path) for path in sorted(assets | {"layout.json"})}
    report = args.output / "diagnostics.json"
    dedupe_args = [] if args.dedupe_images is None else ["--dedupe-images", str(args.dedupe_images)]
    strict = subprocess.run([sys.executable, "-m", "psd2ui", "export", str(args.source),
                             "--output", str(args.output), "--strict", "--report", str(report), *dedupe_args],
                            capture_output=True, text=True, encoding="utf-8")
    (args.validation / "test-export-strict.log").write_text(strict.stdout + strict.stderr, encoding="utf-8")
    assert strict.returncode == int(diagnostics.failed(strict=True)), "Unexpected strict result"
    after = {path: sha(args.output / path) for path in before}
    assert before == after, "Exports differ"
    assert original == sha(args.source), "Source file was modified"
    assert json.loads(report.read_text(encoding="utf-8")) == [d.to_dict() for d in diagnostics.items]
    psd = PSDImage.open(args.source)
    flattened_groups = []
    masked_groups = []
    def check_effect_groups(source_group, exported_group, ancestry=()):
        layers = [layer for layer in source_group if "#" not in layer.name]
        if exported_group.get("layout"):
            axis = 0 if exported_group["layout"] == "horizontal" else 1
            layers.sort(key=lambda layer: layer.bbox[axis])
        for layer, node in zip(layers, exported_group["children"], strict=True):
            if not layer.is_group():
                continue
            styled = layer.effects.enabled and any(effect.enabled for effect in layer.effects)
            masked = layer.has_mask() or layer.has_vector_mask()
            if styled or masked:
                visual = node["children"][0] if node["type"] == "container" else node
                if node["type"] == "container":
                    assert len(node["children"]) == 1, layer.name
                assert visual["type"] == "image" and "children" not in visual, layer.name
                if styled:
                    flattened_groups.append("/".join((*ancestry, layer.name)))
                if masked:
                    masked_groups.append("/".join((*ancestry, layer.name)))
            elif tag_component(layer.name) not in ("GImage", "GLoader"):
                assert node["type"] == "container", layer.name
                check_effect_groups(layer, node, (*ancestry, layer.name))
    check_effect_groups(psd, layout)
    psd.topil().save(args.output / "psd-embedded-preview.png")
    summary = {"source": args.source.name, "sourceSha256": original,
               "canvas": layout["size"], "topLevelNodes": len(layout["children"]),
               "nodes": dict(Counter(n["type"] for n in all_nodes)),
               "uniquePngFiles": len(assets),
               "autoFlattenedEffectGroups": len(flattened_groups),
               "autoFlattenedMaskGroups": len(masked_groups),
               "diagnostics": dict(Counter(d.code for d in diagnostics.items)),
               "repeatableLayoutAndPng": True, "sourceUnchanged": True,
               "strictExitCode": strict.returncode}
    if args.dedupe_images is not None:
        summary["dedupeImageSimilarity"] = args.dedupe_images
    (args.validation / "export.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

