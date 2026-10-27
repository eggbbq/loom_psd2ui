"""Read-only PSD diagnostics and image-name migration CLI frontends."""
import argparse,json
from pathlib import Path


def check_design_main(argv=None,*,root=None):
    root=Path(root or Path.cwd()).resolve();parser=argparse.ArgumentParser(description='只读PSD规范检查')
    parser.add_argument('source',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args(argv)
    try:
        from .design_audit import check_source
        report,output=check_source(args.source,args.report,root=root)
        print(json.dumps(report,ensure_ascii=False,indent=2));print('报告：'+str(output))
        return 0 if report['valid'] else 1
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('PSD 规范检查失败：'+str(error),file=__import__('sys').stderr);return 1


def migrate_names_main(argv=None,*,root=None):
    root=Path(root or Path.cwd()).resolve();parser=argparse.ArgumentParser(description='保留UUID的UI短图名迁移；默认预览')
    parser.add_argument('--project',type=Path,default=Path('client'));parser.add_argument('--laya-assets-dir',type=Path)
    parser.add_argument('--records-dir',type=Path,default=Path('out/psd-export'));parser.add_argument('--apply',action='store_true');args=parser.parse_args(argv)
    try:
        from .image_name_migration import migrate
        project=(root/args.project).resolve();assets=(root/args.laya_assets_dir).resolve() if args.laya_assets_dir else project/'assets/ui'
        result=migrate(project,assets,root/args.records_dir,apply=args.apply);print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('图片名迁移失败：'+str(error),file=__import__('sys').stderr);return 1
