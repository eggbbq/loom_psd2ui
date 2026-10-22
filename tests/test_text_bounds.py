import json
from pathlib import Path

import pytest
from psd_tools import PSDImage
from psd_tools.psd.descriptor import Descriptor, Double

from psd2ui.cli import main
from psd2ui.diagnostics import Diagnostics
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from psd2ui.text import text_bounds
from tests.fixture_factory import group, text


def set_bounds(layer, values, transform):
    layer._data.text_data[b"bounds"] = Descriptor(items={key: Double(value) for key, value in
        zip((b"Left", b"Top ", b"Rght", b"Btom"), values)})
    layer._data.transform = transform


def test_ink_bbox_is_not_the_text_layout_origin(tmp_path):
    psd = PSDImage.new("RGBA", (750, 1624))
    layer = text(psd, value="Lv 10", xy=(39, 116))
    set_bounds(layer, (0, -33.9996337890625, 86, 7.9998779296875),
               (1, 0, 0, 1, 36, 137.9996337890625))
    # The existing pixel cache still starts at (39,116); it must not define Text placement.
    assert layer.bbox[:2] == (39, 116)
    diagnostics = Diagnostics()
    assert text_bounds(layer, diagnostics, "Lv 10") == (36, 104, 122, 145.9995)
    assert not diagnostics.items


@pytest.mark.parametrize("bounds,transform,expected", [
    ((-30, -20, 30, 10), (2, 0, 0, 2, 100, 200), (40, 160, 160, 220)),
    ((0, -20, 40, 10), (0, 1, -1, 0, 100, 200), (90, 200, 120, 240)),
    ((0, -10, 40, 10), (-1, 0, 0, 1, 100, 200), (60, 190, 100, 210)),
])
def test_text_bounds_transform_corners(tmp_path, bounds, transform, expected):
    psd = PSDImage.new("RGBA", (300, 300))
    layer = text(psd)
    set_bounds(layer, bounds, transform)
    assert text_bounds(layer, Diagnostics(), "Text") == expected


def test_text_layout_bounds_flow_into_relative_coordinates_and_prefab(tmp_path):
    psd = PSDImage.new("RGBA", (750, 1624))
    panel = group(psd, "Panel")
    layer = text(panel, value="Lv 10", xy=(39, 116))
    set_bounds(layer, (0, -34, 86, 8), (1, 0, 0, 1, 36, 138))
    source = tmp_path / "text.psd"
    psd.save(source)
    output = tmp_path / "export"
    root = export_psd(source, output)
    parent = root["children"][0]
    node = parent["children"][0]
    assert parent["position"] == [36, 104] and parent["size"] == [86, 42]
    assert node["position"] == [0, 0] and node["size"] == [86, 42]
    project = tmp_path / "project"
    project.mkdir()
    result = generate_prefab(output / "layout.json", project)
    prefab = json.loads(Path(result["prefab"]).read_text())
    parent = prefab["_$child"][0]
    node = parent["_$child"][0]
    assert (parent["x"] + node["x"], parent["y"] + node["y"]) == (36, 104)
    assert (node["width"], node["height"]) == (86, 42)


@pytest.mark.parametrize("kind", ["missing", "inverted", "singular"])
def test_unreadable_layout_bounds_warn_and_fail_strict(tmp_path, kind):
    psd = PSDImage.new("RGBA", (200, 200))
    layer = text(psd)
    if kind == "missing":
        del layer._data.text_data[b"bounds"]
    elif kind == "inverted":
        set_bounds(layer, (10, 10, 0, 0), (1, 0, 0, 1, 20, 25))
    else:
        set_bounds(layer, (0, 0, 90, 32), (0, 0, 0, 0, 20, 25))
    diagnostics = Diagnostics()
    assert text_bounds(layer, diagnostics, "Text") == layer.bbox
    assert diagnostics.items[0].code == "UNREADABLE_TEXT_BOUNDS"
    source = tmp_path / "fallback.psd"
    psd.save(source)
    assert main(["export", str(source), "--output", str(tmp_path / "out"), "--strict"]) == 1

