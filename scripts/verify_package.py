"""Install a Git package snapshot in a clean venv and smoke-test outside the repo.

Only package sources/metadata enter the temporary Git repository. No editable
install, development dependencies, PSD fixtures or Laya project are available
to the installed code. Pass --engine-dir to also exercise real GPU validation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--playwright-module", type=Path)
    parser.add_argument("--report", type=Path, default=ROOT / "out/validation/package/report.json")
    args = parser.parse_args()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    if args.playwright_module:
        env["NINEGRID_PLAYWRIGHT_MODULE"] = str(args.playwright_module.resolve())
    with tempfile.TemporaryDirectory(prefix="psd2ui-package-") as temporary:
        base = Path(temporary)
        source, work, venv = base / "git-source", base / "workspace", base / "venv"
        source.mkdir()
        work.mkdir()
        for name in ("pyproject.toml", "README.md"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "src", source / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "tests", "docs"))

        def run(command, *, cwd=work):
            print("RUN", " ".join(map(str, command)), flush=True)
            return subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)

        run(["git", "init", "-q"], cwd=source)
        run(["git", "add", "."], cwd=source)
        run(["git", "-c", "user.name=Package test", "-c", "user.email=package-test@localhost",
             "commit", "-qm", "Package installation test"], cwd=source)
        run([sys.executable, "-m", "venv", venv])
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        bin_dir = python.parent
        run([python, "-m", "pip", "install", "git+" + source.as_uri()])
        run([python, "-m", "pip", "check"])
        for name in ("psd2ui", "ninegrid", "psd2ui-export", "ninegrid-run"):
            run([bin_dir / (name + (".exe" if os.name == "nt" else "")), "--help"])

        # Generate fixtures using only the installed libraries; also prove both
        # modules and their Node helper came from the isolated environment.
        run([python, "-c", '''
import json, sys, uuid
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
import psd2ui, ninegrid
from ninegrid.reconstruct import reconstruct_9slice
assert Path(psd2ui.__file__).is_relative_to(sys.prefix)
assert Path(ninegrid.__file__).is_relative_to(sys.prefix)
assert Path(ninegrid.__file__).with_name("engine_probe.mjs").is_file()
psd = PSDImage.new("RGBA", (100, 100))
for i in range(2):
    PixelLayer.frompil(Image.new("RGBA", (10, 12), (30, 40, 50, 255)),
                      parent=psd, name="img_Example" + str(i), left=i*20, top=5)
psd.save("fixture.psd")
project = Path("project")
assets = project / "assets/panels"
assets.mkdir(parents=True)
(project / "Demo.laya").write_text('{"version":"3.4.1"}')
rng = np.random.default_rng(17)
small = rng.integers(0, 256, (9, 11, 4), dtype=np.uint8)
image = reconstruct_9slice(small, dict(top=3,right=4,bottom=5,left=6), (60,40))
uid = str(uuid.uuid4())
for index in range(2):
    name = "panel" + str(index)
    Image.fromarray(image).save(assets / (name + ".png"))
    texture_id = str(uuid.uuid5(uuid.UUID(uid), name))
    (assets / (name + ".png.meta")).write_text(json.dumps({"uuid":texture_id,"importer":{"textureType":2,"filterMode":0}}))
    (assets / (name + ".lh")).write_text(json.dumps({"_$ver":1,"_$id":name,"_$type":"GImage","width":60,"height":40,"src":"res://"+texture_id,"autoSize":False}))
'''])

        def command(name, *arguments):
            run([bin_dir / (name + (".exe" if os.name == "nt" else "")), *arguments])

        original = hashlib.sha256((work / "fixture.psd").read_bytes()).digest()
        command("psd2ui", "export", "fixture.psd", "--output", "exported", "--flat-assets",
                "--workers", "2", "--dedupe-images", ".99")
        command("psd2ui", "bundle", "exported/layout.json")
        command("psd2ui", "prefab", "exported/layout.json", "--project", "project")
        command("psd2ui-export", "--input", "fixture.psd", "--dedupe-images", ".99", "--workers", "2")
        assert (work / "laya-project/assets/ui/fixture/fixture.lh").is_file()
        assert not (work / ".venv").exists()
        command("ninegrid", "scan", "--project", "project", "--input", "assets/panels/panel0.png", "--workers", "2")
        command("ninegrid-run", "--project", "project", "--search-dir", "assets/panels",
                "--output", "assets/generated", "--build-only", "--workers", "2")
        command("ninegrid", "verify", "--project", "project", "--workers", "2")
        manifest = json.loads((work / "project/.ninegrid/manifest.json").read_text())
        assert len(manifest["items"]) == 2
        if args.engine_dir:
            command("ninegrid", "apply", "--project", "project", "--workers", "2",
                    "--engine-dir", str(args.engine_dir.resolve()))
            proof = json.loads((work / "project/.ninegrid/validation/report.json").read_text())
            assert proof["valid"]
        assert original == hashlib.sha256((work / "fixture.psd").read_bytes()).digest()
        report = dict(valid=True, installation="pip install git+file:// (isolated Git snapshot)",
                      dependencies="clean venv; pip check passed", commands=4,
                      export=True, bundle=True, prefab=True, export_runner=True,
                      ninegrid_multiprocess_build_verify=True, gpu_verified=bool(args.engine_dir),
                      repository_scripts_required=False)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
