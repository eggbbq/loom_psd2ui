"""Copy the locked engine's runtime and declarations into the local example."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("engine", type=Path, help="LayaAir 3.4.1 source/build root (contains build/libs, build/types)")
args = parser.parse_args()
base = args.engine / "build"
version = json.loads((args.engine / "package.json").read_text())["version"]
if version != "3.4.1":
    parser.error(f"Expected locked engine 3.4.1; got {version}")
target = Path(__file__).resolve().parents[1] / "runtimes/layaair3/example/vendor"
target.mkdir(parents=True, exist_ok=True)
hashes = {}
for relative in ["libs/laya.core.js", "libs/laya.webgl_2D.js", "libs/laya.opengl_2D.js", "types/LayaAir.d.ts"]:
    source = base / relative
    shutil.copy2(source, target / source.name)
    hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
(target / "engine-lock.json").write_text(json.dumps({"version": version, "sha256": hashes}, indent=2) + "\n")
shutil.copy2(args.engine / "LICENSE", target / "LICENSE")
print(f"Prepared LayaAir {version}: {target}")

