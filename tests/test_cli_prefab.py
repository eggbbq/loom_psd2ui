import json
from pathlib import Path

from psd2ui.cli import main
from tests.fixture_factory import make_fixture


def test_installed_cli_generates_portable_bundle_and_project_prefab(tmp_path):
    source = make_fixture(tmp_path / "input.psd")
    output = tmp_path / "exported"
    assert main(["export", str(source), "--output", str(output), "--flat-assets"]) == 0
    assert main(["bundle", str(output / "layout.json")]) == 0
    assert (output / "input.lh").is_file()
    project = tmp_path / "project"
    project.mkdir()
    assert main(["prefab", str(output / "layout.json"), "--project", str(project)]) == 0
    prefab = project / "assets/PSD2UI/input.lh"
    assert prefab.is_file()
    assert json.loads(prefab.read_text())["_$type"] == "GWidget"


def test_prefab_cli_error_returns_failure_without_creating_output(tmp_path, capsys):
    assert main(["bundle", str(tmp_path / "missing.json")]) == 1
    assert "ERROR PREFAB_FAILED" in capsys.readouterr().err
    assert not list(tmp_path.rglob("*.lh"))
