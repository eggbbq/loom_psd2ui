import hashlib
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage
import pytest

from psd2ui.diagnostics import Diagnostics, ExportError
from psd2ui.exporter import export_psd
from tests.fixture_factory import group, pixel, make_fixture
from tests.test_group_effects import add_effect
from tests.test_group_masks import create_group_mask


def snapshot(output):
    return {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.rglob("*") if p.is_file()}


def test_process_export_matches_all_serial_bytes_and_diagnostics_for_real_layered_psd(tmp_path):
    source = make_fixture(tmp_path / "fixture.psd")
    snapshots, diagnostics = [], []
    for workers in (1, 2):
        output = tmp_path / str(workers)
        d = Diagnostics()
        export_psd(source, output, d, workers=workers, flat_assets=True, dedupe_images=0.99)
        snapshots.append(snapshot(output))
        diagnostics.append([i.to_dict() for i in d.items])
    assert snapshots[0] == snapshots[1]
    assert diagnostics[0] == diagnostics[1]


def test_parallel_effects_masks_hidden_layers_and_same_name_overwrites_are_deterministic(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    for index, style in enumerate(("Stroke", "OuterGlow")):
        parent = group(psd, f"Styled{index}", visible=False)
        pixel(parent, "Fill", "red", (20, 20), (30, 25))
        add_effect(parent, style)
    masked = group(psd, "Masked")
    pixel(masked, "Fill", "blue", (20, 20), (30, 30))
    create_group_mask(masked, Image.new("L", (30, 30), 128), top=20, left=20)
    # Same asset path with different canvas/crop origins, across independent jobs.
    pixel(psd, "img_Same", "red", (8, 10), (20, 10))
    pixel(psd, "img_Same", "green", (40, 50), (25, 15))
    source = tmp_path / "effects.psd"
    psd.save(source)
    results = []
    for workers in (1, 2):
        output = tmp_path / str(workers)
        d = Diagnostics()
        root = export_psd(source, output, d, workers=workers)
        results.append((root, snapshot(output), [i.to_dict() for i in d.items]))
    assert results[0] == results[1]


def test_worker_render_failure_preserves_existing_export(tmp_path):
    source = make_fixture(tmp_path / "fixture.psd")
    output = tmp_path / "out"
    export_psd(source, output)
    before = snapshot(output)
    # Invalid name must still fail in the parent, even with jobs in flight.
    psd = PSDImage.open(source)
    pixel(psd, "img_", "red")
    psd.save(source)
    with pytest.raises(ExportError):
        export_psd(source, output, workers=2)
    assert snapshot(output) == before


@pytest.mark.parametrize("value", [-1, True])
def test_invalid_process_count_is_rejected(tmp_path, value):
    source = make_fixture(tmp_path / "fixture.psd")
    with pytest.raises(ValueError):
        export_psd(source, tmp_path / "out", workers=value)


def test_source_change_during_export_does_not_publish_mixed_results(tmp_path, monkeypatch):
    from psd2ui.exporter import Exporter
    source = make_fixture(tmp_path / "fixture.psd")
    output = tmp_path / "out"
    export_psd(source, output)
    before = snapshot(output)
    original = Exporter.build

    def build_and_change(self, path):
        result = original(self, path)
        source.write_bytes(source.read_bytes() + b"changed")
        return result

    monkeypatch.setattr(Exporter, "build", build_and_change)
    diagnostics = Diagnostics()
    with pytest.raises(ExportError):
        export_psd(source, output, diagnostics, workers=2)
    assert diagnostics.items[-1].code == "SOURCE_CHANGED"
    assert snapshot(output) == before


def test_automatic_parallelism_respects_memory_and_manual_override(tmp_path, monkeypatch):
    from psd2ui.parallel import render_worker_count
    source = tmp_path / "large.psd"
    with source.open("wb") as stream:
        stream.truncate(64 * 1024**2)
    monkeypatch.setattr("psd2ui.parallel.os.sysconf", lambda key: 4096 if key == "SC_PAGE_SIZE" else 16 * 1024**3 // 4096)
    monkeypatch.setattr("psd2ui.parallel.worker_count", lambda value: value or 12)
    assert render_worker_count(source, 0, 500) == 6
    assert render_worker_count(source, 12, 500) == 12
    assert render_worker_count(source, 12, 3) == 3
