"""Generic component entrypoints, caller environments and failure publication."""
from pathlib import Path
import hashlib,json
from copy import deepcopy
from unittest.mock import patch
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import Group,PixelLayer
from psd2ui.ui.api import run_export,export_environment
from psd2ui.ui.all_ui import export_command,DEFAULTS
from psd2ui.shared_images.cli import main as shared_main
import pytest


def fixture(root):
    project=root/'client';(project/'assets').mkdir(parents=True);(project/'Demo.laya').write_text('{"version":"3.4.2"}')
    psd=PSDImage.new('RGBA',(128,96));page=Group.new(psd,'ExamplePanel');bg=Group.new(page,'bg');PixelLayer.frompil(Image.new('RGBA',(128,96),'#204060'),parent=bg,name='artwork');content=Group.new(page,'content');img=Group.new(content,'img_panel');PixelLayer.frompil(Image.new('RGBA',(47,23),'#8090a0'),parent=img,name='artwork',left=9,top=13);source=root/'Example.psd';psd.save(source)
    return source,project,project/'assets/ui',root/'records'


def identity(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def test_public_component_api_reexports_and_does_not_publish_a_failed_check(tmp_path):
    source,project,assets,records=fixture(tmp_path);before=source.read_bytes()
    result=run_export(tmp_path,[source],project,assets,records,export_only=True,workers=1)
    assert result['valid'] and source.read_bytes()==before
    first=identity(assets);run_export(tmp_path,[source],project,assets,records,export_only=True,workers=1)
    assert identity(assets)==first
    with patch('psd2ui.ui.workflow.audit',side_effect=ValueError('injected final check')):
        with pytest.raises(ValueError,match='injected final check'):run_export(tmp_path,[source],project,assets,records,export_only=True,workers=1)
    assert identity(assets)==first and source.read_bytes()==before


def test_batch_command_is_an_installed_module_and_carries_playwright(tmp_path):
    module=tmp_path/'node_modules/playwright/index.js'
    with export_environment(root=tmp_path,playwright_module=module):
        command=export_command(tmp_path,deepcopy(DEFAULTS))
    assert command[1:3]==['-m','psd2ui.ui']
    assert command[command.index('--playwright-module')+1]==str(module)
    assert not any('export_psd.py' in p for p in command)


def test_shared_cli_relative_inventory_uses_explicit_root_and_reports_failure(tmp_path,monkeypatch,capsys):
    source,project,assets,records=fixture(tmp_path);run_export(tmp_path,[source],project,assets,records,export_only=True,workers=1)
    names=[p.name for p in (assets/'images').glob('*.png')];(tmp_path/'preferred.json').write_text(json.dumps(names))
    other=tmp_path/'unrelated';other.mkdir();monkeypatch.chdir(other)
    assert shared_main(['--project','client','--state-dir','shared-state','--existing-images','preferred.json'],root=tmp_path)==0
    assert shared_main(['--project','client','--state-dir','shared-state','--existing-images','missing.json'],root=tmp_path)==1
    assert str(tmp_path/'missing.json') in capsys.readouterr().err
