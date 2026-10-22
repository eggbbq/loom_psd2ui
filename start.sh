#!/usr/bin/env bash
# Export PSD, generate the native prefab, build and serve the native Laya project.
set -euo pipefail

# PSD 导出参数：直接修改下面的值；注释 --dedupe-images 行可关闭去重。
SOURCE_PSD="test.psd"
OUTPUT_DIR="out/test"
args=(
    export             "$SOURCE_PSD"
    --output           "$OUTPUT_DIR"
    --report           "$OUTPUT_DIR/diagnostics.json"
    --dedupe-images    0.99
    # --strict
)

# 浏览器预览参数；命令行也可传 --port、--no-open 覆盖。
preview_args=(
    --port             8765
    # --no-open
)

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

case "${1:-}" in
    -h|--help)
        echo '用法: ./start.sh [--port 8765] [--no-open]'
        echo '默认读取 test.psd，生成原生 .lh，再构建并预览 LayaAir 工程。'
        echo '导出参数在脚本顶部 args=(...) 中修改，默认图片去重阈值为 0.99。'
        echo '需要 LayaAir CLI 3.4.1，可用 LAYAAIR_CLI 指定可执行文件。'
        echo 'PSD2UI_REEXPORT=1 强制重新导出。按 Ctrl+C 停止服务。'
        exit 0
        ;;
esac

command -v python3 >/dev/null 2>&1 || { echo '需要安装 Python 3.11+。' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "需要 Python 3.11+")'

LAYA_CLI="${LAYAAIR_CLI:-$(command -v layaair || true)}"
if [ -z "$LAYA_CLI" ] && [ -x "$HOME/.layaair/layaair" ]; then
    LAYA_CLI="$HOME/.layaair/layaair"
fi
if [ -z "$LAYA_CLI" ] || [ ! -x "$LAYA_CLI" ]; then
    echo '需要 LayaAir CLI 3.4.1；可用 LAYAAIR_CLI=/path/to/layaair ./start.sh 指定。' >&2
    exit 1
fi
if [ "$("$LAYA_CLI" --version)" != '3.4.1' ]; then
    echo '该工程锁定 LayaAir CLI 3.4.1，请选择对应版本。' >&2
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo '创建 Python 虚拟环境…'
    python3 -m venv .venv
fi
PYTHON="$PROJECT_DIR/.venv/bin/python"
if ! "$PYTHON" -c 'import psd2ui, psd_tools, PIL, scipy, skimage, aggdraw' >/dev/null 2>&1; then
    echo '安装 Python 依赖…'
    "$PYTHON" -m pip install -e '.[dev]'
fi

export_cache() {
    "$PYTHON" - "$1" "$SOURCE_PSD" "$OUTPUT_DIR" "${args[@]}" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path
mode, source, output, *arguments = sys.argv[1:]
source, output = Path(source), Path(output)
layout, cache = output / 'layout.json', output / '.start-export.json'
if not source.is_file():
    raise SystemExit(f'未找到 {source}')
def settings():
    return {'arguments': arguments, 'layoutSha256': hashlib.sha256(layout.read_bytes()).hexdigest()}
if mode == 'save':
    staged = cache.with_suffix('.tmp')
    staged.write_text(json.dumps(settings(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    staged.replace(cache)
    raise SystemExit(0)
inputs = [source, *(p for p in Path('src/psd2ui').glob('*.py') if p.name != 'laya_prefab.py')]
def missing_asset(node):
    return (node.get('type') == 'image' and not (layout.parent / node['asset']).is_file()) or any(
        missing_asset(child) for child in node.get('children', []))
try:
    incomplete = missing_asset(json.loads(layout.read_text(encoding='utf-8')))
    changed = json.loads(cache.read_text(encoding='utf-8')) != settings()
except (OSError, ValueError, KeyError, TypeError, AttributeError):
    incomplete, changed = True, True
print(int(os.environ.get('PSD2UI_REEXPORT') == '1' or incomplete or changed or not layout.is_file() or
          any(p.stat().st_mtime > layout.stat().st_mtime for p in inputs)))
PY
}
NEEDS_EXPORT=$(export_cache check)
if [ "$NEEDS_EXPORT" = 1 ]; then
    echo "导出 ${SOURCE_PSD}（复杂效果提示详见 ${OUTPUT_DIR}/diagnostics.json）…"
    mkdir -p out/validation
    if ! "$PYTHON" -m psd2ui "${args[@]}" >out/validation/start-export.log 2>&1; then
        tail -30 out/validation/start-export.log >&2
        exit 1
    fi
    tail -1 out/validation/start-export.log
    export_cache save
fi

echo '从 layout.json 生成 LayaAir 原生预制体…'
"$PYTHON" scripts/sync_laya_project.py --source-output "$OUTPUT_DIR"
echo '构建原生 LayaAir 工程…'
mkdir -p out/validation
if ! "$LAYA_CLI" build web --project "$PROJECT_DIR/laya-project" --skip-package-install \
        >out/validation/laya-project-build.log 2>&1; then
    tail -40 out/validation/laya-project-build.log >&2
    exit 1
fi
tail -1 out/validation/laya-project-build.log
exec "$PYTHON" scripts/preview_server.py "${preview_args[@]}" "$@"

