"""Read documented configuration and invoke the transactional PSD workflow."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

from .audit import audit
from .verify_export import verify_exported_resize
from .ninegrid_names import normalize_ignored_names

DEFAULTS={
    'paths':dict(project='client',assets='client/assets/ui',sources='.',records='out/psd-export',reports='out/ui-export-reports'),
    'export':dict(workers=2,ninegrid_mode='visual',ninegrid_ignore_names=['icon','ico','图标'],dedupe_similarity=1.0,pixel_grid=True,button_down_effect='dark',strict=False),
    'layout':dict(content_align_x='',content_align_y='',content_align_config=''),
    'checks':dict(resize=True,repair_records=[]),
}


def load_config(path):
    with Path(path).open('rb') as file:data=tomllib.load(file)
    if set(data)-set(DEFAULTS):raise ValueError('配置包含未知分组')
    result={}
    for section,defaults in DEFAULTS.items():
        values=data.get(section,{})
        if not isinstance(values,dict) or set(values)-set(defaults):raise ValueError(f'无效配置分组：{section}')
        result[section]={**defaults,**values}
        for key,value in result[section].items():
            expected=type(defaults[key]);valid=type(value) is expected if expected is not float else type(value) in (int,float)
            if not valid:raise ValueError(f'[{section}].{key} 类型错误')
    options=result['export']
    options['ninegrid_ignore_names']=list(normalize_ignored_names(options['ninegrid_ignore_names']))
    if options['workers']<0 or not 0<=options['dedupe_similarity']<=1:raise ValueError('workers 或 dedupe_similarity 超出范围')
    if options['ninegrid_mode'] not in {'visual','strict'}:raise ValueError('ninegrid_mode 必须是 visual/strict')
    if options['button_down_effect'] not in {'none','dark','up-scale','down-scale'}:raise ValueError('button_down_effect 不受支持')
    for key,choices in [('content_align_x',{'','auto','left','center','right'}),('content_align_y',{'','auto','top','center','bottom'})]:
        if result['layout'][key] not in choices:raise ValueError(f'{key} 不受支持')
    if any(not isinstance(p,str) or not p.strip() for p in result['checks']['repair_records']):raise ValueError('repair_records 必须是路径数组')
    if any(not p for p in result['paths'].values()):raise ValueError('配置路径不能为空')
    return result


def export_command(root,config):
    paths={k:(root/value).resolve() for k,value in config['paths'].items()};options=config['export']
    command=[sys.executable,'-m','psd2ui.ui','--all','--source-dir',str(paths['sources']),
        '--project',str(paths['project']),'--laya-assets-dir',str(paths['assets']),'--records-dir',str(paths['records']),
        '--workers',str(options['workers']),'--mode',options['ninegrid_mode'],'--dedupe-images',str(options['dedupe_similarity']),
        '--button-down-effect',options['button_down_effect'],'--ninegrid-ignore-names',json.dumps(options['ninegrid_ignore_names'],ensure_ascii=False)]
    from .environment import playwright_module
    if playwright_module() is not None:command.extend(['--playwright-module',str(playwright_module())])
    if not options['pixel_grid']:command.append('--no-pixel-grid')
    if options['strict']:command.append('--strict')
    if not config['checks']['resize']:command.append('--no-resize-check')
    for directory in config['checks']['repair_records']:command.extend(['--repair-records',str((root/directory).resolve())])
    for key,value in config['layout'].items():
        if value:command.extend(['--'+key.replace('_','-'),str((root/value).resolve()) if key=='content_align_config' else value])
    return command


def _run(root,config,*,check_only=False):
    root=Path(root).resolve();paths={k:(root/value).resolve() for k,value in config['paths'].items()}
    if not paths['assets'].is_relative_to(paths['project']/'assets'):raise ValueError('assets 必须在 Laya 工程 assets 内')
    if any(paths[key].is_relative_to(paths['project']) for key in ('records','reports')):raise ValueError('记录和报告须在 Laya 工程外')
    paths['reports'].mkdir(parents=True,exist_ok=True)
    report=Path(tempfile.mkdtemp(prefix='run-',dir=paths['reports']))
    if not check_only:
        command=export_command(root,config)+['--report-dir',str(report)]
        with (report/'export.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in process.stdout:
                log.write(line);log.flush();print(line.rstrip(),flush=True)
            code=process.wait()
        if code:raise RuntimeError(f'导出失败（{code}），未发布本次资源。日志：{report/"export.log"}')
        return json.loads((report/'summary.json').read_text())
    repairs=[root/path for path in config['checks']['repair_records']]
    resources=audit(report/'resources.json',project=paths['project'],assets=paths['assets'],records=paths['records'],quiet=True,
                    ignored_names=config['export']['ninegrid_ignore_names'],repair_records=repairs)
    resize=verify_exported_resize(report/'resize-project',paths['project'],paths['assets'],paths['records'],repair_records=repairs) if config['checks']['resize'] else None
    summary=dict(valid=True,checkOnly=True,resources=resources,resize=resize,reportDirectory=str(report),
                 engineCases=resources['engineCases']+(resize['cases'] if resize else 0))
    content=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    (report/'summary.json').write_text(content);(paths['reports']/'latest.json').write_text(content)
    print(f'检查通过：{report/"summary.json"}',flush=True)
    return summary


def run(root,config,*,check_only=False,playwright_module=None):
    from .environment import export_environment
    with export_environment(root=root,playwright_module=playwright_module):
        return _run(root,config,check_only=check_only)
