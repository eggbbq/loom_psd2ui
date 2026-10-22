import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from psd_tools import PSDImage

import start
from tests.fixture_factory import group, pixel


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    source = tmp_path / "商城 测试.psd"
    psd = PSDImage.new("RGBA", (60, 80))
    pixel(group(psd, "Shop"), "img_Picture", "red", (10, 20), (8, 6))
    psd.save(source)
    script = tmp_path / "scripts/generate_asset_bundle.py"
    script.parent.mkdir()
    shutil.copy2(start.ROOT / "scripts/generate_asset_bundle.py", script)
    monkeypatch.setattr(start, "ensure_python", lambda root: Path(sys.executable))
    args = start.parser().parse_args(["--input", source.name, "--dedupe-images", "0.99"])
    target = tmp_path / "laya-project/assets/ui" / source.stem
    return tmp_path, args, source, target


def contents(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes()
            for p in directory.rglob("*") if p.is_file()}


def test_pipeline_moves_bundle_and_reuses_cache_and_project_metadata(pipeline, capsys):
    root, args, source, target = pipeline
    start.run(args, root)
    assert (target / (source.stem + ".lh")).is_file()
    assert (target / "Shop/Picture.png").is_file()
    assert not (root / source.stem).exists()
    assert not (target / "assets").exists()
    assert not (target / source.stem).exists()
    meta_path = target / "Shop/Picture.png.meta"
    meta = json.loads(meta_path.read_text())
    meta["importer"]["filterMode"] = 0
    meta_path.write_text(json.dumps(meta))
    before = contents(target)
    capsys.readouterr()
    start.run(args, root)
    assert f"导出 {args.input}（" not in capsys.readouterr().out
    # The generator normalizes JSON formatting; the existing importer is intact.
    assert json.loads(meta_path.read_text()) == meta
    after = contents(target)
    assert {p: b for p, b in before.items() if not p.endswith(".meta")} == {
        p: b for p, b in after.items() if not p.endswith(".meta")}
    assert not (root / source.stem).exists()
    assert not list((root / "out/validation").glob("start-move.*"))


@pytest.mark.parametrize("change", ["missing_png", "layout", "parameters", "force"])
def test_pipeline_reexports_when_cached_output_is_no_longer_valid(pipeline, capsys, change):
    root, args, source, target = pipeline
    start.run(args, root)
    if change == "missing_png":
        (target / "Shop/Picture.png").unlink()
    elif change == "layout":
        layout = json.loads((target / "layout.json").read_text())
        layout["size"] = [1, 1]
        (target / "layout.json").write_text(json.dumps(layout))
    elif change == "parameters":
        args.dedupe_images = 1
    else:
        args.reexport = True
    capsys.readouterr()
    start.run(args, root)
    assert f"导出 {args.input}（" in capsys.readouterr().out
    assert json.loads((target / "layout.json").read_text())["size"] == [60, 80]
    assert (target / "Shop/Picture.png").is_file()


def test_export_failure_preserves_previous_laya_bundle(pipeline):
    root, args, source, target = pipeline
    start.run(args, root)
    before = contents(target)
    args.report = Path(source.stem) / "Shop/Picture.png"
    with pytest.raises(subprocess.CalledProcessError):
        start.run(args, root)
    assert contents(target) == before


@pytest.mark.parametrize("existing", [True, False])
def test_failed_move_restores_target_and_keeps_staged_output(tmp_path, monkeypatch, existing):
    output, target = tmp_path / "staged", tmp_path / "target"
    output.mkdir()
    (output / "new").write_text("new")
    if existing:
        target.mkdir()
        (target / "old").write_text("old")
    rename = Path.rename

    def fail_output(path, destination):
        if path == output:
            raise OSError("simulated move failure")
        return rename(path, destination)

    monkeypatch.setattr(Path, "rename", fail_output)
    with pytest.raises(OSError, match="simulated move failure"):
        start.move_bundle(output, target, tmp_path / "backups")
    assert (output / "new").read_text() == "new"
    assert target.exists() == existing
    if existing:
        assert (target / "old").read_text() == "old"
    assert not list((tmp_path / "backups").glob("start-move.*"))


@pytest.mark.parametrize("output", [".", "src/generated", "laya-project/assets/ui/商城 测试"])
def test_invalid_staging_directory_is_rejected_before_environment_setup(pipeline, monkeypatch, output):
    root, args, _, target = pipeline
    args.output = Path(output)

    def forbidden(root):
        pytest.fail("Invalid paths must be rejected before environment setup")

    monkeypatch.setattr(start, "ensure_python", forbidden)
    with pytest.raises(ValueError):
        start.run(args, root)
    assert not target.exists()
