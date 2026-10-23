"""Prepare Python, export a PSD bundle, then move it into a LayaAir project."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


_SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CHECKOUT = ((_SOURCE_ROOT / "pyproject.toml").is_file() and
                   (_SOURCE_ROOT / "src/psd2ui/run_export.py").resolve() == Path(__file__).resolve())
ROOT = _SOURCE_ROOT if SOURCE_CHECKOUT else Path.cwd()

if SOURCE_CHECKOUT and __package__ in (None, ""):
    sys.path.insert(0, str(ROOT / "src"))


def parser():
    result = argparse.ArgumentParser(description="导出 PSD、生成同名预制体，并将整个目录移动到 Laya 工程。")
    result.add_argument("--input", required=True, type=Path,
                        help="PSD / PSB 路径；源码模式相对仓库根目录，pip 安装后相对当前工作目录")
    result.add_argument("--workers", type=workers_value, default=0, help="合成进程数：0 按 CPU 和内存自动选择，1 单进程，或填写如 4/8")
    result.add_argument("--output", type=Path, help="临时导出目录，默认使用 PSD 文件名（不含扩展名）")
    result.add_argument("--laya-assets-dir", type=Path, default=Path("laya-project/assets/ui"),
                        help="Laya 资源父目录，不存在时自动创建")
    result.add_argument("--report", type=Path, help="诊断路径，默认 <输出目录>/diagnostics.json")
    result.add_argument("--flat-assets", action=argparse.BooleanOptionalAction, default=True,
                        help="直接按 PSD 分组存放 PNG，不额外套 assets 层（默认开启）")
    result.add_argument("--dedupe-images", type=similarity, metavar="X",
                        help="启用图片去重，相似度阈值 0～1；省略则关闭")
    result.add_argument("--strict", action="store_true", help="启用严格导出模式")
    result.add_argument("--reexport", action="store_true", help="忽略缓存，强制重新导出 PSD")
    return result


def workers_value(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("workers 必须大于等于 0")
    return number


def similarity(value):
    number = float(value)
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("图片相似度必须在 0～1 之间")
    return number


def ensure_python(root):
    """Bootstrap with stdlib only; all exporter commands use the local venv."""
    if not SOURCE_CHECKOUT:
        return Path(sys.executable)
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("创建 Python 虚拟环境…", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], check=True)
    check = subprocess.run([str(python), "-c", "import psd2ui, psd_tools, PIL, scipy, skimage, aggdraw"],
                           cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode:
        print("安装 Python 依赖…", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-e", ".[dev]"], cwd=root, check=True)
    return python


def cache_settings(layout, arguments):
    return {"arguments": arguments, "layoutSha256": hashlib.sha256(layout.read_bytes()).hexdigest()}


def needs_export(source, output, arguments, root, force=False):
    layout = output / "layout.json"
    if force:
        return True

    def missing_asset(node):
        return (node.get("type") == "image" and not (output / node["asset"]).is_file()) or any(
            missing_asset(child) for child in node.get("children", []))

    try:
        if missing_asset(json.loads(layout.read_text(encoding="utf-8"))):
            return True
        cached = json.loads((output / ".start-export.json").read_text(encoding="utf-8"))
        if cached != cache_settings(layout, arguments):
            return True
        inputs = [source, *(p for p in Path(__file__).parent.glob("*.py") if p.name != "laya_prefab.py")]
        return any(p.stat().st_mtime > layout.stat().st_mtime for p in inputs)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return True


def save_cache(output, arguments):
    cache = output / ".start-export.json"
    staged = cache.with_suffix(".tmp")
    staged.write_text(json.dumps(cache_settings(output / "layout.json", arguments),
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(cache)


def preserve_metadata(output, target):
    # Prefer the project's existing UUIDs and importer settings.
    for meta in target.rglob("*.meta"):
        staged = output / meta.relative_to(target)
        if staged.with_suffix("").is_file():
            shutil.copy2(meta, staged)


def move_bundle(output, target, backup_parent):
    """Replace the directory without nesting it; restore the old target on failure."""
    backup = None
    if target.exists():
        backup_parent.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="start-move.", dir=backup_parent))
        try:
            target.rename(backup / "previous")
        except BaseException:
            backup.rmdir()
            raise
    try:
        output.rename(target)
    except BaseException:
        if backup is not None:
            (backup / "previous").rename(target)
            backup.rmdir()
        raise
    if backup is not None:
        shutil.rmtree(backup)


def run(args, root=ROOT):
    source = (root / args.input).resolve()
    output_arg = args.output if args.output is not None else Path(source.stem)
    report_arg = args.report if args.report is not None else output_arg / "diagnostics.json"
    output = root / output_arg
    target = root / args.laya_assets_dir / source.stem
    if not source.is_file():
        raise ValueError(f"未找到 {source}")
    if output.is_symlink() or target.is_symlink():
        raise ValueError("导出目录和 Laya 目标目录不能是符号链接")
    output, target = output.resolve(), target.resolve()
    protected = [root / name for name in (".git", ".venv", "src", "scripts", "tests", "runtimes", "laya-project")]
    if output in (root, root / "out") or any(output.is_relative_to(p) for p in protected):
        raise ValueError(f"导出目录与项目目录冲突：{output}")
    if output.is_relative_to(target) or target.is_relative_to(output):
        raise ValueError("临时导出目录和 Laya 目标目录不能相同或互相包含")
    for path in (output, target):
        if path.exists() and not path.is_dir():
            raise ValueError(f"目标不是普通目录：{path}")

    python = ensure_python(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_dir() and not output.exists():
        shutil.copytree(target, output)

    arguments = ["export", str(args.input), "--output", str(output_arg), "--report", str(report_arg)]
    if args.flat_assets:
        arguments.append("--flat-assets")
    if args.dedupe_images is not None:
        arguments.extend(("--dedupe-images", str(args.dedupe_images)))
    if args.strict:
        arguments.append("--strict")
    validation = root / "out/validation"
    if needs_export(source, output, arguments, root, args.reexport or os.environ.get("PSD2UI_REEXPORT") == "1"):
        print(f"导出 {args.input}（复杂效果提示详见 {report_arg}）…", flush=True)
        validation.mkdir(parents=True, exist_ok=True)
        log_path = validation / "start-export.log"
        command = [str(python), "-u", "-m", "psd2ui", *arguments, "--workers", str(args.workers)]
        with log_path.open("w", encoding="utf-8") as log:
            with subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, encoding="utf-8", errors="replace") as process:
                for line in process.stdout:
                    log.write(line)
                    if line.startswith(("PSD 合成进程：", "[PSD 图片合成]", "[PSD 图片编码]", "EXPORTED:")):
                        print(line.rstrip(), flush=True)
                result = subprocess.CompletedProcess(command, process.wait())
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if result.returncode:
            print("\n".join(lines[-30:]), flush=True)
        result.check_returncode()
        save_cache(output, arguments)

    print("生成 LayaAir 预制体和资源元数据…", flush=True)
    preserve_metadata(output, target)
    subprocess.run([str(python), "-m", "psd2ui", "bundle", str(output / "layout.json")],
                   cwd=root, check=True)
    move_bundle(output, target, validation)
    print(f"导出并移动完成：{target}/", flush=True)


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.version_info < (3, 11):
        print("需要 Python 3.11+。", file=sys.stderr)
        return 1
    try:
        run(args)
    except subprocess.CalledProcessError as exc:
        print(f"执行失败，退出码 {exc.returncode}；原 Laya 目录保留。", file=sys.stderr)
        return exc.returncode if exc.returncode > 0 else 1
    except (OSError, ValueError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
