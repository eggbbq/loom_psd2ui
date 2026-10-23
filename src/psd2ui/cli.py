import argparse
import json
import sys
from pathlib import Path

from .diagnostics import Diagnostic, Diagnostics, ExportError
from .deduplication import similarity_threshold
from .exporter import export_psd


def main(argv=None):
    parser = argparse.ArgumentParser(prog="psd2ui", description="Export layered PSD/PSB without Photoshop")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("export", help="Export layout.json and PNG assets")
    command.add_argument("source", type=Path)
    command.add_argument("--output", required=True, type=Path)
    command.add_argument("--workers", type=int, default=1, help="Render processes: 0 CPU/RAM auto, 1 serial, or e.g. 4/8")
    command.add_argument("--strict", action="store_true", help="Fail on fidelity/style warnings (duplicate paths are allowed)")
    command.add_argument("--report", type=Path, help="Write a JSON array of diagnostics")
    command.add_argument("--dedupe-images", type=similarity_threshold, metavar="X",
                         help="Deduplicate same-size RGBA images at similarity >= X (0..1; 1 is exact; default off)")
    command.add_argument("--flat-assets", action="store_true",
                         help="Write PSD folders and PNGs directly under output, without an assets directory")
    bundle = commands.add_parser("bundle", help="Generate a portable .lh and .meta files beside layout.json")
    bundle.add_argument("layout", type=Path)
    prefab = commands.add_parser("prefab", help="Generate a prefab and textures in a Laya project")
    prefab.add_argument("layout", type=Path)
    prefab.add_argument("--project", type=Path, required=True)
    prefab.add_argument("--output", help="Prefab path relative to the Laya project")
    prefab.add_argument("--scene", help="Optional existing project-relative .ls to place the prefab")
    args = parser.parse_args(argv)
    if args.command in ("bundle", "prefab"):
        from .laya_prefab import generate_asset_bundle, generate_prefab
        try:
            result = (generate_asset_bundle(args.layout) if args.command == "bundle" else
                      generate_prefab(args.layout, args.project, args.output, args.scene))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERROR PREFAB_FAILED: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    diagnostics = Diagnostics()
    success = False
    try:
        if args.report and (args.report.resolve() in {args.source.resolve(), (args.output / "layout.json").resolve()} or
                            args.report.resolve().is_relative_to((args.output / "assets").resolve()) or
                            args.report.resolve().is_relative_to(args.output.resolve()) and args.report.suffix.lower() == ".png"):
            diagnostics.fail("INVALID_REPORT_PATH", str(args.report), "Report cannot overwrite input, layout.json or PNG assets")
        export_psd(args.source, args.output, diagnostics, dedupe_images=args.dedupe_images,
                   flat_assets=args.flat_assets, workers=args.workers, progress=print)
        success = True
    except ExportError:
        pass
    except Exception as exc:
        diagnostics.items.append(Diagnostic(
            "EXPORT_FAILED", "error", str(args.source), f"{type(exc).__name__}: {exc}"))
    if args.report:
        try:
            if (args.report.resolve() in {args.source.resolve(), (args.output / "layout.json").resolve()} or
                    args.report.resolve().is_relative_to((args.output / "assets").resolve()) or
                    args.report.resolve().is_relative_to(args.output.resolve()) and args.report.suffix.lower() == ".png"):
                raise ValueError("Report path would overwrite input or layout")
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps([d.to_dict() for d in diagnostics.items], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"ERROR REPORT_FAILED: {exc}", file=sys.stderr)
            success = False
    for d in diagnostics.items:
        print(f"{d.severity.upper()} {d.code} [{d.psdPath}] {d.message}", file=sys.stderr)
    failed = diagnostics.failed(args.strict) or not success
    print(f"{'FAILED' if failed else 'EXPORTED'}: {args.output / 'layout.json'}; {len(diagnostics.items)} diagnostics")
    return 1 if failed else 0

