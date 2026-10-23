import hashlib

import numpy as np
from PIL import Image, ImageCms
from psd_tools import PSDImage
from psd_tools.api import pil_io
import pytest

from psd2ui.color import _transform, apply_icc
from psd2ui.deduplication import deduplicate_images, image_nodes
from psd2ui.exporter import export_psd
from tests.fixture_factory import group, pixel
from tests.test_deduplication import make_dedupe_fixture


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).digest()
            for p in directory.rglob("*") if p.is_file()}


def test_cached_icc_matches_library_pixels_including_transparent_rgb_and_reuses_transform(monkeypatch):
    _transform.cache_clear()
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    rng = np.random.default_rng(246)
    builds = []
    original = ImageCms.buildTransformFromOpenProfiles

    def build(*args, **kwargs):
        builds.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(ImageCms, "buildTransformFromOpenProfiles", build)
    for mode, channels in (("RGB", 3), ("RGBA", 4)):
        values = rng.integers(0, 256, (40, 60, channels), dtype=np.uint8)
        if mode == "RGBA":
            values[:10, :, 3] = 0
        image = Image.fromarray(values, mode)
        for _ in range(2):
            actual = apply_icc(image, profile)
            expected = pil_io._apply_icc(image, profile)
            assert actual.mode == expected.mode
            assert actual.tobytes() == expected.tobytes()
    assert len(builds) == 1  # Both paths use an RGB working image.
    assert _transform.cache_info().maxsize == 8
    _transform.cache_clear()


def test_invalid_icc_preserves_library_error():
    image = Image.new("RGBA", (3, 4), (13, 21, 35, 127))
    for convert in (apply_icc, pil_io._apply_icc):
        with pytest.raises(OSError):
            convert(image, b"invalid profile")


def test_incompatible_icc_preserves_library_fallback_and_diagnostic(caplog):
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    image = Image.new("CMYK", (3, 4))
    actual = apply_icc(image, profile)
    assert actual is image
    assert "Failed to apply ICC profile" in caplog.text


@pytest.mark.parametrize("threshold", [0, .99, 1])
@pytest.mark.parametrize("workers", [1, 2])
def test_deferred_encoding_matches_png_then_deduplicate_bytes(tmp_path, threshold, workers):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    expected = tmp_path / "expected"
    # Use the public file-based deduplicator as an independent reference for
    # the previous algorithm, including floating thresholds and first-match order.
    root = export_psd(source, expected, workers=1)
    duplicates = deduplicate_images(root, expected, threshold)
    for asset in duplicates:
        (expected / asset).unlink()
    actual = tmp_path / "actual"
    result = export_psd(source, actual, workers=workers, dedupe_images=threshold)
    assert result == root
    assert {p: h for p, h in snapshot(expected).items() if p.endswith(".png")} == {
        p: h for p, h in snapshot(actual).items() if p.endswith(".png")}
    assert not list(actual.rglob("*.rgba"))
    assert not list(actual.glob(".psd2ui-*"))


def test_only_retained_images_are_png_encoded(tmp_path, monkeypatch):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    encodings = []
    original = Image.Image.save

    def save(self, fp, format=None, **kwargs):
        if format == "PNG":
            encodings.append(self.size)
        return original(self, fp, format=format, **kwargs)

    monkeypatch.setattr(Image.Image, "save", save)
    root = export_psd(source, tmp_path / "output", dedupe_images=.99)
    assert len(encodings) == 2
    assert len({n["asset"] for n in image_nodes(root)}) == 2


@pytest.mark.parametrize("workers", [1, 2])
def test_last_same_path_overwrite_is_used_before_deduplication(tmp_path, workers):
    psd = PSDImage.new("RGBA", (100, 100))
    pixel(psd, "First", "red", (2, 3), (6, 7))
    pixel(psd, "Same", "red", (15, 20), (6, 7))
    pixel(psd, "Same", "blue", (40, 50), (8, 9))
    pixel(psd, "Last", "blue", (60, 70), (8, 9))
    source = tmp_path / "input.psd"
    psd.save(source)
    output = tmp_path / "output"
    root = export_psd(source, output, dedupe_images=1, workers=workers)
    first, same1, same2, last = root["children"]
    assert same1["asset"] == same2["asset"] == last["asset"]
    assert first["asset"] != same1["asset"]
    assert same1["size"] == same2["size"] == [8, 9]
    assert same1["position"] == [15, 20]
    with Image.open(output / same1["asset"]) as image:
        assert image.getpixel((0, 0)) == (0, 0, 255, 255)


def test_png_encoding_failure_keeps_previous_export_and_removes_raw_stage(tmp_path, monkeypatch):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    output = tmp_path / "output"
    export_psd(source, output, dedupe_images=.99)
    before = snapshot(output)

    def fail(*args):
        raise OSError("PNG encoding failed")

    monkeypatch.setattr("psd2ui.exporter.encode_raster", fail)
    with pytest.raises(OSError, match="PNG encoding failed"):
        export_psd(source, output, dedupe_images=.99)
    assert snapshot(output) == before
    assert not list(output.glob(".psd2ui-*"))


def test_raw_memory_limit_spill_and_same_asset_replacement(tmp_path):
    from psd2ui.rasters import RasterStore

    store = RasterStore(tmp_path, memory_limit=64)
    with Image.new("RGBA", (4, 4), (20, 30, 40, 0)) as image:
        store.put("same", store.write(image))
        assert store.memory_bytes == 64
        store.put("disk", store.write(image))
        disk_path = store.entries["disk"]["path"]
        assert "data" not in store.entries["disk"]
        with store.load("disk") as loaded:
            assert loaded.tobytes() == image.tobytes()
        store.put("same", store.write(image))
        assert store.memory_bytes == 0
        store.put("disk", store.write(image))
        assert store.memory_bytes == 64
        from pathlib import Path
        assert not Path(disk_path).exists()


@pytest.mark.parametrize("workers", [1, 2])
def test_first_match_uses_final_hbox_order_instead_of_psd_render_order(tmp_path, workers):
    psd = PSDImage.new("RGBA", (100, 100))
    parent = group(psd, "hbox_Items")
    for name, x, value in (("Right", 20, 100), ("Left", 0, 102), ("Last", 40, 104)):
        pixel(parent, name, (value, 0, 0, 255), (x, 0), (10, 10))
    source = tmp_path / "input.psd"
    psd.save(source)
    root = export_psd(source, tmp_path / "output", workers=workers, dedupe_images=.99)
    nodes = list(image_nodes(root))
    assert [n["name"] for n in nodes] == ["Left", "Right", "Last"]
    assert {n["asset"] for n in nodes} == {"assets/Items/Left.png"}
