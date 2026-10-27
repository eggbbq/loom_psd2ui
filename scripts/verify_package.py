"""Verify disjoint PSD/NineGrid wheels outside source repositories.

A real SDK render is enabled by --engine-dir; CPU-only checks never claim GPU
success. No editable installation or temporary Git commit is performed.
"""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--ninegrid-wheel',type=Path,required=True)
    parser.add_argument('--engine-dir',type=Path)
    parser.add_argument('--playwright-module',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    with tempfile.TemporaryDirectory(prefix='psd2ui-package-') as temporary:
        base=Path(temporary);work=base/'workspace';work.mkdir();venv=base/'venv'
        def run(command):return subprocess.run(list(map(str,command)),cwd=work,env=env,check=True)
        run([sys.executable,'-m','venv',venv]);python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        run([python,'-m','pip','install',args.wheel.resolve(),args.ninegrid_wheel.resolve()]);run([python,'-m','pip','check'])
        for module in ['psd2ui','psd2ui.ui','ninegrid'] :run([python,'-m',module,'--help'])
        run([python,'-c','''
from pathlib import Path
from importlib.metadata import distribution,packages_distributions
import json,sys
import psd2ui,ninegrid
from psd_tools import PSDImage
from psd_tools.api.layers import Group,PixelLayer
from PIL import Image
from psd2ui.ui.api import run_export
assert Path(psd2ui.__file__).is_relative_to(sys.prefix)
assert Path(ninegrid.__file__).is_relative_to(sys.prefix)
assert packages_distributions()['ninegrid']==['loom-image9grid']
a={str(p) for p in distribution('psd2ui').files};b={str(p) for p in distribution('loom-image9grid').files};assert not a&b
assert not any(p.startswith('ninegrid/') for p in a)
assert Path(psd2ui.__file__).parent.joinpath('ui/runtime/UIListDecoration.ts').is_file()
p=Path.cwd();project=p/'project';(project/'assets').mkdir(parents=True);(project/'Demo.laya').write_text('{"version":"3.4.2"}')
psd=PSDImage.new('RGBA',(128,96));page=Group.new(psd,'PackagePanel');bg=Group.new(page,'bg');PixelLayer.frompil(Image.new('RGBA',(128,96),'#204060'),parent=bg,name='artwork');content=Group.new(page,'content');img=Group.new(content,'img_panel');PixelLayer.frompil(Image.new('RGBA',(47,23),'#8090a0'),parent=img,name='artwork',left=9,top=13);psd.save(p/'Components.psd')
r=run_export(p,[p/'Components.psd'],project,project/'assets/ui',p/'records',export_only=True,workers=1);assert r['valid']
'''])
        run([python,'-m','psd2ui.ui','Components.psd','--project','project','--records-dir','records','--export-only','--workers','1'])
        if args.engine_dir:
            command=[python,'-m','psd2ui.ui','Components.psd','--project','project','--records-dir','records','--workers','1','--engine-dir',args.engine_dir.resolve()]
            if args.playwright_module:command.extend(['--playwright-module',args.playwright_module.resolve()])
            run(command)
        report=dict(valid=True,installation='two non-editable wheels; clean venv; external cwd',uniqueNinegridOwner='loom-image9grid',disjointRecord=True,publicComponentApi=True,publicComponentCli=True,packagedRuntime=True,gpuVerified=bool(args.engine_dir))
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
