import json
from pathlib import Path

import pytest
from psd_tools import PSDImage

from psd2ui.diagnostics import Diagnostics
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel


@pytest.mark.parametrize("prefix,axis,gap,field", [("hbox_", 0, 7, "columnGap"), ("vbox_", 1, 9, "rowGap")])
def test_spacing_uses_psd_edges_with_different_sizes_and_spatial_order(tmp_path, prefix, axis, gap, field):
    psd = PSDImage.new("RGBA", (160, 160))
    parent = group(psd, prefix + "Items")
    sizes = [10, 20, 15]
    starts = [20, 20 + 10 + gap, 20 + 30 + 2 * gap]
    for index in (2, 0, 1):
        xy = [10, 10]
        xy[axis] = starts[index]
        size = [8, 8]
        size[axis] = sizes[index]
        pixel(parent, str(index), "red", xy, size, visible=index != 1)
    source = tmp_path / "spacing.psd"
    psd.save(source)
    diagnostics = Diagnostics()
    layout = export_psd(source, tmp_path / "out", diagnostics)
    container = layout["children"][0]
    assert container["component"] == "GBox" and container["gap"] == gap
    assert [child["name"] for child in container["children"]] == ["0", "1", "2"]
    assert not container["children"][1]["visible"]
    assert not diagnostics.items
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(tmp_path / "out/layout.json", project)
    native = json.loads(Path(result["prefab"]).read_text())["_$child"][0]
    assert native["layout"][field] == gap


def test_uneven_spacing_uses_mean_and_reports_loss(tmp_path):
    psd = PSDImage.new("RGBA", (100, 100))
    parent = group(psd, "hbox_Items")
    for index, x in enumerate((10, 30, 60)):
        pixel(parent, str(index), "red", (x, 10), (10, 10))
    source = tmp_path / "uneven.psd"
    psd.save(source)
    diagnostics = Diagnostics()
    layout = export_psd(source, tmp_path / "out", diagnostics)
    assert layout["children"][0]["gap"] == 15
    assert [item.code for item in diagnostics.items] == ["NON_UNIFORM_LAYOUT_GAP"]
    assert diagnostics.failed(strict=True)


@pytest.mark.parametrize("count", [0, 1])
def test_empty_or_single_child_layout_uses_zero_gap(tmp_path, count):
    psd = PSDImage.new("RGBA", (40, 40))
    parent = group(psd, "vbox_Items")
    if count:
        pixel(parent, "Only", "red", (10, 10))
    source = tmp_path / "small.psd"
    psd.save(source)
    assert export_psd(source, tmp_path / "out")["children"][0]["gap"] == 0


def test_overlapping_items_keep_negative_gap(tmp_path):
    psd = PSDImage.new("RGBA", (40, 40))
    parent = group(psd, "hbox_Items")
    pixel(parent, "First", "red", (5, 10), (16, 16))
    pixel(parent, "Second", "blue", (15, 10), (16, 16))
    source = tmp_path / "overlap.psd"
    psd.save(source)
    assert export_psd(source, tmp_path / "out")["children"][0]["gap"] == -6
