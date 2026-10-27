"""Independent shared-image restoration, exact dedupe and reference updates."""
import argparse,json,sys
from pathlib import Path


def main(argv=None, *, root=None):
    ROOT=Path(root or Path.cwd()).resolve()
    from psd2ui.deduplication import similarity_threshold
    from .pipeline import run
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path('client'))
    parser.add_argument('--laya-assets-dir',type=Path)
    parser.add_argument('--state-dir',type=Path,default=Path('out/psd-export/shared-image-dedupe'))
    parser.add_argument('--threshold',type=similarity_threshold,default=1)
    parser.add_argument('--existing-images',type=Path,help='导入前已有图片名的 JSON 清单，优先保留')
    parser.add_argument('--fresh-prefabs',nargs='*',default=[],help='本次新导入的预制体文件名')
    parser.add_argument('--restore-only',action='store_true',help='导入前恢复共享依赖，防止源页面重导出覆盖其他页面')
    parser.add_argument('--source-records',type=Path,action='append',default=[],help='附加原图身份/九宫格记录目录，用于识别历史不同切图')
    args=parser.parse_args(argv);project=(ROOT/args.project).resolve()
    assets=(ROOT/args.laya_assets_dir).resolve() if args.laya_assets_dir else project/'assets/ui'
    try:
        preferred=json.loads((ROOT/args.existing_images).read_text()) if args.existing_images else None
        result=run(project,assets,ROOT/args.state_dir,threshold=args.threshold,preferred=preferred,
                   fresh_prefabs=args.fresh_prefabs,restore_only=args.restore_only,source_records=[ROOT/p for p in args.source_records])
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(f'跨页面去重失败：{error}；去重事务未提交，已导入页面保持可用。',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
