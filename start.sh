#!/usr/bin/env bash
set -euo pipefail

# 修改参数即可；输出目录和预制体名称默认使用 PSD 文件名。
args=(
    --input            "商城_给程序.psd"
    --laya-assets-dir  "laya-project/assets/ui"
    --flat-assets
    --dedupe-images    0.99
    # --output         "商城_给程序"
    # --strict
    # --reexport
)

exec python3 "$(dirname -- "$0")/start.py" "${args[@]}" "$@"
