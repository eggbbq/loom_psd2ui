"""Normalized component PSD → LayaAir UI CLI; legacy CLI remains separate."""
from pathlib import Path
import argparse
import json
import subprocess


def parser():
    from psd2ui.run_export import similarity, workers_value
    from psd2ui.ui.layout import BUTTON_DOWN_EFFECTS
    result=argparse.ArgumentParser(description=__doc__)
    result.add_argument('source',nargs='?',type=Path)
    result.add_argument('--input',type=Path,help='与位置参数二选一')
    result.add_argument('--all',action='store_true')
    result.add_argument('--source-dir',type=Path,default=Path('.'),help='--all 扫描此目录内平铺 PSD/PSB')
    result.add_argument('--plan',action='store_true',help='只检查结构和映射，不写导出资源')
    result.add_argument('--inspect',action='store_true',help='只打印 psd-tools 原始中立树，便于核对图层')
    result.add_argument('--page-canvas',action=argparse.BooleanOptionalAction,default=None,help='默认自动识别单页背景覆盖画布；可显式覆盖')
    result.add_argument('--trim-static-smartobjects',action=argparse.BooleanOptionalAction,default=None,help='默认自动收紧异常巨大透明缓存；保留icon及全透明尺寸标记')
    result.add_argument('--font-alias-config',type=Path,help='显式字体family/bold映射JSON；保留PSD与native中的源字体')
    result.add_argument('--project',type=Path,default=Path('client'))
    result.add_argument('--laya-assets-dir',type=Path)
    result.add_argument('--records-dir',type=Path,default=Path('out/psd-export'))
    result.add_argument('--report-dir',type=Path)
    result.add_argument('--strict',action='store_true')
    result.add_argument('--dedupe-images',type=similarity,default=1)
    result.add_argument('--no-dedupe-images',dest='dedupe_images',action='store_const',const=None)
    result.add_argument('--export-only',action='store_true',help='跳过九宫格及 WebGL 验证；仍检查资源与引用')
    result.add_argument('--pixel-grid',action=argparse.BooleanOptionalAction,default=True)
    result.add_argument('--mode',choices=('visual','strict'),default='visual')
    result.add_argument('--ninegrid-ignore-names',type=json.loads)
    result.add_argument('--workers',type=workers_value,default=2)
    result.add_argument('--button-down-effect',choices=BUTTON_DOWN_EFFECTS,default='dark')
    result.add_argument('--engine-dir',type=Path)
    result.add_argument('--playwright-module',type=Path,help='显式Playwright模块入口，不打包node_modules')
    result.add_argument('--content-align-x',choices=('auto','left','center','right'))
    result.add_argument('--content-align-y',choices=('auto','top','center','bottom'))
    result.add_argument('--content-align-config',type=Path)
    result.add_argument('--resize-check',action=argparse.BooleanOptionalAction,default=True)
    result.add_argument('--repair-records',type=Path,action='append',default=[])
    return result


def _main(argv, root):
    ROOT=Path(root).resolve()
    cli=parser();args=cli.parse_args(argv)
    if args.source and args.input:cli.error('PSD 路径只能指定一次')
    source=args.source or args.input
    if bool(source)==args.all:cli.error('指定 PSD 路径或 --all，二选一')
    try:
        from psd2ui.ui.exporter import discover,export_feature
        from psd2ui.ui.alignment import load_content_alignment_config
        from psd2ui.ui.ninegrid_names import configured_ignore_names,normalize_ignored_names
        from psd2ui.psd.source import PSDSource
        sources=discover(ROOT/args.source_dir,ROOT/source if source else None)
        source_options=dict(page_canvas=args.page_canvas,trim_static_smartobjects=args.trim_static_smartobjects)
        from psd2ui.ui.font_aliases import load_font_aliases
        font_aliases=load_font_aliases(ROOT/args.font_alias_config) if args.font_alias_config else None
        config=load_content_alignment_config(ROOT/args.content_align_config) if args.content_align_config else None
        ignored=configured_ignore_names() if args.ninegrid_ignore_names is None else normalize_ignored_names(args.ninegrid_ignore_names)
        project=(ROOT/args.project).resolve()
        assets=(ROOT/args.laya_assets_dir).resolve() if args.laya_assets_dir else project/'assets/ui'
        options=dict(strict=args.strict,dedupe=args.dedupe_images,export_only=args.export_only,mode=args.mode,
                     workers=args.workers,engine_dir=(ROOT/args.engine_dir).resolve() if args.engine_dir else None,
                     button_down_effect=args.button_down_effect,content_align_x=args.content_align_x,
                     content_align_y=args.content_align_y,content_align_config=config,pixel_grid=args.pixel_grid,
                     ninegrid_ignore_names=ignored)
        options['font_aliases']=font_aliases
        if args.plan or args.inspect:
            with PSDSource(**source_options) as adapter:
                for source in sources:
                    result=adapter.open(source) if args.inspect else export_feature(adapter,source,project,assets,plan_only=True,**options)
                    print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0
        if not args.export_only and not any(project.glob('*.laya')):raise ValueError(f'未找到有效 Laya 工程：{project}')
        from psd2ui.ui.workflow import run_export
        run_export(ROOT,sources,project,assets,(ROOT/args.records_dir).resolve(),
                   report_dir=(ROOT/args.report_dir).resolve() if args.report_dir else None,
                   resize=args.resize_check,repair_records=[ROOT/p for p in args.repair_records],rebuilding_all=args.all,
                   source_options=source_options,playwright_module=(ROOT/args.playwright_module).resolve() if args.playwright_module else None,**options)
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as error:
        if hasattr(error, 'diagnostics'):
            print(json.dumps(error.diagnostics,ensure_ascii=False,indent=2))
        print(f'PSD 导出未完成：{error}；本次暂存未发布，源 PSD 不会修改。',file=__import__('sys').stderr)
        return 1


def main(argv=None, *, root=None, playwright_module=None, config_path=None):
    from .environment import export_environment
    root=Path(root or Path.cwd()).resolve()
    with export_environment(root=root,playwright_module=playwright_module,config_path=config_path):
        return _main(argv,root)


if __name__=='__main__':raise SystemExit(main())
