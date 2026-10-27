"""Configured batch export/check CLI for normalized component PSDs."""
import argparse,subprocess
from pathlib import Path

def main(argv=None,*,root=None,playwright_module=None):
    root=Path(root or Path.cwd()).resolve();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('export_all_ui.toml'))
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--playwright-module',type=Path)
    args=parser.parse_args(argv)
    try:
        from .all_ui import load_config,run
        run(root,load_config(root/args.config),check_only=args.check_only,
            playwright_module=root/args.playwright_module if args.playwright_module else playwright_module)
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(f'UI 流程未完成：{error}',file=__import__('sys').stderr);return 1
