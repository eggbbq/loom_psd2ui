"""Source entrypoints keep bootstrap and repository-relative paths after moving."""
from pathlib import Path
import subprocess
import sys

import pytest
from psd_tools import PSDImage

from ninegrid import run_9grid
from psd2ui import run_export
from tests.fixture_factory import pixel


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module,script", [
    (run_export, "src/psd2ui/run_export.py"),
    (run_9grid, "src/ninegrid/run_9grid.py"),
])
def test_direct_source_entrypoint_help_without_site_packages(module, script, tmp_path):
    assert module.ROOT == ROOT
    result = subprocess.run([sys.executable, "-I", "-S", str(ROOT / script), "--help"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--workers" in result.stdout


@pytest.mark.parametrize("script", ["run_export.sh", "run_9grid.sh"])
def test_shell_help_from_another_directory(script, tmp_path):
    result = subprocess.run(["bash", str(ROOT / script), "--help"], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--workers" in result.stdout


def test_export_shell_runs_moved_source_entrypoint_from_another_directory(tmp_path):
    source = tmp_path / "shell fixture.psd"
    psd = PSDImage.new("RGBA", (30, 40))
    pixel(psd, "img_Example", (20, 30, 40, 255), (3, 5), (6, 8))
    psd.save(source)
    target = tmp_path / "laya-assets"
    result = subprocess.run([
        "bash", str(ROOT / "run_export.sh"), "--input", str(source),
        "--output", str(tmp_path / "staged"), "--laya-assets-dir", str(target),
        "--workers", "2",
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    bundle = target / source.stem
    assert (bundle / "Example.png").is_file()
    assert (bundle / (source.stem + ".lh")).is_file()
    assert not (tmp_path / "staged").exists()
