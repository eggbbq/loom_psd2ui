import copy
import hashlib
from io import BytesIO

import numpy as np
from PIL import Image

from .candidate import choose_candidate
from .crop import png_bytes
from .manifest import MANIFEST, read_manifest, markdown_report
from .paths import inside, relative, sha256, load_json, json_bytes
from .scan import read_rgba
from .verify import verify_item, verify_project
from .laya.adapter import LayaProjectAdapter, source_importer_reason
from .laya.references import unsafe_reason
from .laya.patch import commit
from .visual import choose_visual_candidate, quality_limits


def scan(adapter, inputs=None, output="assets/ninegrid_auto", min_saving=0.20, *,
         mode="strict", quality=None, center_size=8, axis="auto"):
    root = adapter.project.root
    output_path = inside(root, output)
    input_names = list(inputs or ["assets"])
    overwrite = any(inside(root, name) == output_path for name in input_names)
    if overwrite and any(not inside(root, name).is_relative_to(output_path) for name in input_names):
        raise ValueError("原地写回时，所有搜索路径须位于相同输出目录内；其他目录请分开运行。")
    if not output_path.is_relative_to(adapter.project.assets) or (output_path == adapter.project.assets and not overwrite):
        raise ValueError("Output must be a subdirectory of project assets")
    if not 0 <= min_saving <= 1:
        raise ValueError("min-saving must be between 0 and 1")
    if mode not in ("strict", "visual"):
        raise ValueError("mode must be strict or visual")
    if type(center_size) is not int or not 1 <= center_size <= 64:
        raise ValueError("center-size must be in [1,64]")
    quality = quality or quality_limits()
    excluded = [] if overwrite else [output_path, inside(root, "assets/ninegrid_auto")]
    old = inside(root, MANIFEST)
    if old.exists():
        old_manifest = read_manifest(root)
        if not overwrite and not old_manifest["settings"].get("overwriteSource"):
            excluded.append(inside(root, old_manifest["settings"]["output"]))
        if overwrite:
            excluded.extend(inside(root, item["output"]) for item in old_manifest["items"]
                            if not item.get("overwriteSource"))
    files = set()
    for name in input_names:
        path = inside(root, name)
        if not path.exists() or not path.is_relative_to(adapter.project.assets):
            raise ValueError(f"Input must exist inside project assets: {name}")
        if not overwrite and path.is_relative_to(output_path):
            raise ValueError(
                f"搜索路径 {relative(root, path)} 与输出目录 {relative(root, output_path)} 相同，"
                "或位于输出目录内；输出目录会被排除，因此无法扫描。"
                "请将 --output 改为独立目录，例如 assets/ninegrid_auto。"
                "将 --search-dir 与 --output 填为同一目录即可原地写回。")
        if any(path.is_relative_to(directory) for directory in excluded):
            raise ValueError(
                f"搜索路径 {relative(root, path)} 位于已排除的优化输出目录内；"
                "请将 --search-dir 指向原始 PNG 目录，避免重复优化生成图。")
        candidates = [path] if path.is_file() else path.rglob("*")
        for source in candidates:
            if source.suffix.lower() != ".png" or any(source.is_relative_to(p) for p in excluded):
                continue
            files.add(inside(root, source))
    items = []
    for source in sorted(files):
        name = relative(root, source)
        item = {"source": name, "sourceSha256": sha256(source), "status": "skipped", "reason": None}
        refs = adapter.for_source(source)
        meta_path = inside(root, name + ".meta")
        meta = load_json(meta_path) if meta_path.exists() else {}
        item["sourceMetadata"] = meta
        item["sourceFilterMode"] = meta.get("importer", {}).get("filterMode", 1)
        reason = source_importer_reason(meta)
        atlas = []
        parent = source.parent
        while parent.is_relative_to(adapter.project.assets):
            for config in sorted(parent.glob("*.atlascfg")):
                config = inside(root, config)
                settings = load_json(config)
                if parent != source.parent and not settings.get("includeSubFolders", False):
                    continue
                atlas.append({"file": relative(root, config), "sha256": sha256(config)})
                if (settings.get("scale", 1) != 1 or settings.get("usePng8") or
                        settings.get("platformDefault", {}).get("format", 0) != 0 or settings.get("allowRotation")):
                    reason = reason or "unsupported_atlas_transform"
                if settings.get("filterMode", item["sourceFilterMode"]) != item["sourceFilterMode"]:
                    reason = reason or "atlas_filter_override"
            parent = parent.parent
        if atlas:
            item["atlasConfigurations"] = atlas
            item["warnings"] = ["source_auto_atlas_present_originals_preserved"]
        try:
            rgba = read_rgba(source)
            item["sourceSize"] = list(rgba.shape[1::-1])
            if sha256(source) != item["sourceSha256"]:
                raise ValueError("source_changed_during_scan")
            if reason:
                candidate, algorithm_reason = None, reason
            elif mode == "visual":
                candidate, diff = choose_visual_candidate(rgba, min_saving, quality, center_size, axis)
                algorithm_reason = diff.get("reason")
                item["cpuQuality"] = diff
                item["qualityLimits"] = quality
            else:
                candidate, algorithm_reason = choose_candidate(rgba, min_saving)
            item["reason"] = reason or algorithm_reason
            if candidate:
                item.update(candidate.fields(), status="candidate")
                item["output"] = name if overwrite else relative(root, output_path / source.relative_to(adapter.project.assets))
        except (OSError, ValueError) as exc:
            item["reason"] = str(exc)
        item["references"] = [ref.report(unsafe_reason(ref, item.get("sourceSize", []))) for ref in refs]
        item["safeReferences"] = sum(ref["eligible"] for ref in item["references"])
        items.append(item)
    settings = {"output": relative(root, output_path), "inputs": list(map(str, inputs or ["assets"])), "minSaving": min_saving}
    if mode == "visual":
        settings.update(mode=mode, algorithmVersion=2, qualityLimits=quality, centerSize=center_size, axis=axis)
    report = {"schemaVersion": 1, "projectVersion": adapter.project.version,
            "settings": settings,
            "items": items,
            "summary": {"scanned": len(items), "candidates": sum(i["status"] == "candidate" for i in items),
                        "safeReferences": sum(i["safeReferences"] for i in items)}}
    if overwrite:
        from .inplace import prepare_report
        report["settings"]["overwriteSource"] = True
        prepare_report(adapter, report, old_manifest if old.exists() else {"items": []})
    return report


def build(adapter, inputs=None, output="assets/ninegrid_auto", min_saving=0.20, dry_run=False, *,
          mode="strict", quality=None, center_size=8, axis="auto"):
    root = adapter.project.root
    report = scan(adapter, inputs, output, min_saving, mode=mode, quality=quality, center_size=center_size, axis=axis)
    if report["settings"].get("overwriteSource"):
        from .inplace import build_inplace
        return build_inplace(adapter, report, dry_run)
    old = read_manifest(root) if inside(root, MANIFEST).exists() else {"items": []}
    previous = {item["source"]: item for item in old["items"]}
    manifest = {**copy.deepcopy(old), "schemaVersion": 1, "projectVersion": adapter.project.version,
                "settings": report["settings"], "items": []}
    writes, expected = {}, {}
    for item in report["items"]:
        prior = previous.get(item["source"])
        if prior and any(r.get("applied") for r in prior.get("references", [])):
            verify_item(root, prior)
            if prior["sourceSha256"] != item["sourceSha256"] or old.get("settings") != report["settings"]:
                raise ValueError("Rollback applied changes before rebuilding with changed sources/settings")
            manifest["items"].append(prior)
            continue
        if item["status"] != "candidate":
            continue
        source = inside(root, item["source"])
        rgba = read_rgba(source)
        if mode == "visual":
            candidate, diff = choose_visual_candidate(rgba, min_saving, item["qualityLimits"], center_size, axis)
            reason = diff.get("reason")
        else:
            candidate, reason = choose_candidate(rgba, min_saving)
        if candidate is None or sha256(source) != item["sourceSha256"]:
            raise ValueError(f"Source changed during build: {item['source']}: {reason}")
        cropped = candidate.crop(rgba)
        content = png_bytes(cropped)
        with Image.open(BytesIO(content)) as encoded:
            if not np.array_equal(cropped, np.asarray(encoded.convert("RGBA"))):
                raise ValueError("PNG roundtrip changed RGBA")
        meta = adapter.create_meta(item)
        item = copy.deepcopy(item)
        item.update(status="built", outputSha256=hashlib.sha256(content).hexdigest(), outputUuid=meta["uuid"])
        manifest["items"].append(item)
        for name, data in ((item["output"], content), (item["output"] + ".meta", json_bytes(meta))):
            path = inside(root, name)
            expected[name] = sha256(path) if path.exists() else None
            if path.exists() and not prior:
                raise ValueError(f"Refusing to overwrite unmanaged output: {name}")
            if name.endswith(".meta") and path.exists():
                existing = load_json(path)
                # Preserve IDE importer defaults added after the initial build.
                if existing.get("uuid") != meta["uuid"]:
                    raise ValueError(f"Generated UUID changed: {name}")
                existing.setdefault("importer", {})["sizeGrid"] = meta["importer"]["sizeGrid"]
                existing["importer"]["filterMode"] = meta["importer"]["filterMode"]
                data = json_bytes(existing)
            writes[name] = data
        expected[item["source"]] = item["sourceSha256"]
    # Never silently forget an applied image excluded from this scan.
    for name, prior in previous.items():
        if name not in {i["source"] for i in report["items"]} and any(r.get("applied") for r in prior["references"]):
            raise ValueError("Rollback applied changes before changing input scope")
    writes[MANIFEST] = json_bytes(manifest)
    writes[".ninegrid/report.json"] = json_bytes(report)
    writes[".ninegrid/report.md"] = markdown_report(report).encode("utf-8")
    if dry_run:
        return {"status": "dry_run", "files": sorted(writes), "report": report}
    run_id = commit(root, writes, "build", expected)
    return {"status": "built", "runId": run_id, "manifest": MANIFEST, "report": report}


def apply(adapter, dry_run=False, engine_dir=None, engine_validator=None):
    root = adapter.project.root
    manifest = read_manifest(root)
    if manifest["settings"].get("overwriteSource"):
        from .inplace import apply_inplace
        return apply_inplace(adapter, manifest, dry_run, engine_dir, engine_validator)
    verify_project(adapter, manifest)
    scene_before = adapter.project.scene_hashes
    expected_state = {MANIFEST: sha256(inside(root, MANIFEST))}
    for item in manifest["items"]:
        for name in (item["source"] + ".meta", item["output"] + ".meta"):
            path = inside(root, name)
            expected_state[name] = sha256(path) if path.exists() else None
        for config in item.get("atlasConfigurations", []):
            expected_state[config["file"]] = config["sha256"]
    original_scenes = copy.deepcopy(adapter.project.scenes)
    changes = []
    engine_items = []
    for item in manifest["items"]:
        records = adapter.patch(item)
        applied = [record for record in records if record["eligible"]]
        if applied:
            engine_items.append({"item": item, "types": sorted({r["type"] for r in applied})})
        changes.extend(records)
        # Previously applied records remain authoritative for verify/rollback.
        retained = [r for r in item["references"] if r.get("applied")]
        item["references"] = retained + [{**record, "applied": record["eligible"]} for record in records]
        if any(r.get("applied") for r in item["references"]):
            item["status"] = "applied"
    writes = {name: json_bytes(data) for name, data in adapter.project.scenes.items() if data != original_scenes[name]}
    planned = {"status": "dry_run" if dry_run else "applied", "changes": changes,
               "files": sorted(writes), "engineValidationPending": bool(engine_items)}
    if dry_run:
        return planned
    if not writes:
        return {**planned, "status": "already_applied_or_no_safe_references", "runId": None}
    # Validate all changed images on the actual Laya runtime before scene commit.
    if engine_validator is None:
        from .engine import validate_items
        engine_validator = validate_items
    proof = engine_validator(adapter, engine_items, engine_dir)
    if not proof.get("valid"):
        raise ValueError(f"Engine pixel comparison failed; project scenes unchanged: {proof}")
    manifest["engineValidation"] = proof
    writes[MANIFEST] = json_bytes(manifest)
    writes[".ninegrid/apply-report.json"] = json_bytes({**planned, "engineValidationPending": False,
                                                       "engineValidation": proof})
    expected = {**expected_state, **{name: scene_before[name] for name in writes if name in scene_before}}
    # Recheck source/output pixels after the asynchronous GPU probe.
    for item in manifest["items"]:
        verify_item(root, item)
        expected[item["source"]] = item["sourceSha256"]
        expected[item["output"]] = item["outputSha256"]
    # Every scene patch must still parse before starting the transaction.
    import json
    for name, content in writes.items():
        if name.endswith((".ls", ".lh")):
            json.loads(content)
    run_id = commit(root, writes, "apply", expected, {"references": changes})
    return {**planned, "engineValidationPending": False, "engineValidation": proof, "runId": run_id}
