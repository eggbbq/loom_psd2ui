import copy
import json
from pathlib import Path

import pytest
from PIL import Image
from psd_tools import PSDImage

from psd2ui.cli import main
from psd2ui.deduplication import deduplicate_images, image_nodes
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
from tests.fixture_factory import group, pixel, text


def layout_with_images(output, images):
    children = []
    for name, image in images:
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        children.append(dict(type="image", name=name, asset=name,
                             position=[3, 5], size=list(image.size), visible=True))
    return dict(type="root", children=children)


@pytest.mark.parametrize("channel", range(4))
@pytest.mark.parametrize("difference,threshold,merged", [
    (0, 1, True), (1, 1, False), (2, .99, True), (3, .99, False),
    (2, 1 - 2 / 255, True), (255, 0, True),
])
def test_all_pixels_and_rgba_channels(tmp_path, channel, difference, threshold, merged):
    original = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    altered = original.copy()
    color = [0, 0, 0, 0]
    color[channel] = difference
    altered.putpixel((99, 99), tuple(color))
    root = layout_with_images(tmp_path, [("first.png", original), ("second.png", altered)])
    replacements = deduplicate_images(root, tmp_path, threshold)
    assert replacements == ({"second.png": "first.png"} if merged else {})
    assert root["children"][1]["asset"] == ("first.png" if merged else "second.png")
    # Planning is separate from deletion/publication.
    assert (tmp_path / "second.png").exists()


def test_size_requires_both_dimensions_and_first_layout_reference_wins(tmp_path):
    root = layout_with_images(tmp_path, [
        ("z.png", Image.new("RGBA", (2, 3), "red")),
        ("a.png", Image.new("RGBA", (2, 3), "red")),
        ("wide.png", Image.new("RGBA", (3, 3), "red")),
        ("tall.png", Image.new("RGBA", (2, 4), "red")),
        ("rotated.png", Image.new("RGBA", (3, 2), "red")),
    ])
    second = root["children"].pop(1)
    second["visible"] = False
    root["children"].insert(1, dict(type="container", children=[second, copy.deepcopy(second)]))
    before = copy.deepcopy(root)
    Image.new("RGBA", (2, 3), "red").save(tmp_path / "unreferenced.png")
    assert deduplicate_images(root, tmp_path, 0) == {"a.png": "z.png"}
    for child in root["children"][1]["children"]:
        child["asset"] = "a.png"
    assert root == before  # All other node properties/order preserved.
    assert (tmp_path / "unreferenced.png").exists()


def test_approximate_matches_do_not_chain(tmp_path):
    root = layout_with_images(tmp_path, [
        (f"{i}.png", Image.new("RGBA", (1, 1), (i * 2, 0, 0, 255))) for i in range(3)
    ])
    assert deduplicate_images(root, tmp_path, .99) == {"1.png": "0.png"}
    assert root["children"][2]["asset"] == "2.png"


def make_dedupe_fixture(path):
    psd = PSDImage.new("RGBA", (100, 100))
    pixel(group(psd, "First"), "img_Z", (10, 20, 30, 255), (3, 7))
    pixel(group(psd, "Second", visible=False), "icon_A", (12, 20, 30, 255), (30, 15))
    pixel(psd, "Third", (13, 20, 30, 255), (55, 20))
    text(psd, "title_Caption", "Remain editable")
    psd.save(path)
    return path


def test_export_cli_deletes_duplicates_updates_all_refs_and_generates_prefab(tmp_path):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    original = source.read_bytes()
    output = tmp_path / "output"
    baseline = export_psd(source, output)
    refs = [node["asset"] for node in image_nodes(baseline)]
    assert len(set(refs)) == 3  # Default disabled.
    (output / "unrelated.png").write_bytes(b"leave alone")
    args = ["export", str(source), "--output", str(output), "--dedupe-images", ".99", "--strict"]
    assert main(args) == 0
    result = json.loads((output / "layout.json").read_text())
    assert [node["asset"] for node in image_nodes(result)] == [refs[0], refs[0], refs[2]]
    assert not (output / refs[1]).exists()  # Includes old output from disabled mode.
    assert (output / refs[0]).exists() and (output / refs[2]).exists()
    assert (output / "unrelated.png").read_bytes() == b"leave alone"
    restored = copy.deepcopy(result)
    for node, asset in zip(image_nodes(restored), refs):
        node["asset"] = asset
    assert restored == baseline
    snapshots = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert main(args) == 0
    assert snapshots == {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert source.read_bytes() == original
    project = tmp_path / "project"
    project.mkdir()
    generated = generate_prefab(output / "layout.json", project)
    assert generated["textures"] == 2
    prefab = json.loads(Path(generated["prefab"]).read_text())
    first = prefab["_$child"][0]["_$child"][0]
    second = prefab["_$child"][1]["_$child"][0]
    assert first["_$type"] == "GImage" and second["_$type"] == "GLoader"
    assert first["src"] == second["src"]


def test_dedupe_failure_preserves_previous_output(tmp_path, monkeypatch):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    output = tmp_path / "output"
    export_psd(source, output)
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    def fail(*args):
        raise OSError("PNG read failed")
    monkeypatch.setattr("psd2ui.exporter.deduplicate_images", fail)
    with pytest.raises(OSError):
        export_psd(source, output, dedupe_images=.99)
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}


def test_duplicate_symlink_is_removed_without_deleting_its_target(tmp_path):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    output = tmp_path / "output"
    baseline = export_psd(source, output)
    duplicate = output / list(image_nodes(baseline))[1]["asset"]
    duplicate.unlink()
    unrelated = output / "unrelated.png"
    unrelated.write_bytes(b"keep")
    duplicate.symlink_to(unrelated)
    export_psd(source, output, dedupe_images=.99)
    assert unrelated.read_bytes() == b"keep"
    assert not duplicate.is_symlink()


def test_duplicate_alias_of_kept_png_fails_before_publication(tmp_path):
    source = make_dedupe_fixture(tmp_path / "input.psd")
    output = tmp_path / "output"
    baseline = export_psd(source, output)
    first, duplicate, _ = [output / n["asset"] for n in image_nodes(baseline)]
    duplicate.unlink()
    duplicate.symlink_to(first)
    before = (output / "layout.json").read_bytes(), first.read_bytes()
    with pytest.raises(ValueError, match="alias"):
        export_psd(source, output, dedupe_images=.99)
    assert before == ((output / "layout.json").read_bytes(), first.read_bytes())


@pytest.mark.parametrize("value", ["-0.1", "1.1", "nan", "inf", "-inf", "invalid"])
def test_invalid_threshold_rejected_before_export(tmp_path, value):
    output = tmp_path / "output"
    with pytest.raises(SystemExit) as error:
        main(["export", "missing.psd", "--output", str(output), "--dedupe-images", value])
    assert error.value.code == 2
    with pytest.raises(ValueError):
        export_psd("missing.psd", output, dedupe_images=value)
    assert not output.exists()
