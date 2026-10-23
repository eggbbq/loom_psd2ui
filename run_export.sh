#!/usr/bin/env bash
set -euo pipefail

# 用法：./run_export.sh；修改 args 中的值，或追加参数，例如 --input "test.psd"。
# 相对路径以本脚本目录为基准；路径含空格或中文请加双引号。
# 开关参数单独写，不填 true / false；取消 # 参数行注释即可启用。
args=(
    # PSD / PSB 源文件：必填，可写相对路径或绝对路径。
    # 输出目录及预制体名称默认使用文件名（不含扩展名）。
    --input            "test.psd"

    # PSD 图片合成进程数：填非负整数；0 根据 CPU 和内存自动选择，1 单进程，4/8 指定进程数。
    # 每个进程独立读取 PSD，主进程按原图层顺序写入，保持同名覆盖规则和预制体结果。
    # 调整进程数不会让仍有效的缓存重新导出；需要重新计时可加 --reexport。
    --workers          0

    # Laya 资源父目录：不存在时自动创建；最终移动到 <此目录>/<PSD文件名>/。
    # 例如本配置最终为 laya-project/assets/ui/商城_给程序/。
    --laya-assets-dir  "laya-project/assets/ui"

    # 开关：PNG 直接按 PSD 分组目录存放，不额外套 assets 层（默认已开启）。
    # 若需要恢复额外 assets 层，改为 --no-flat-assets。
    --flat-assets

    # 图片去重阈值：填 0～1 小数，0.99 = RGBA 各通道相似度至少 99%。
    # 仅比较宽高相同的图，复用第一张资源；删除此行即关闭去重。
    --dedupe-images    0.99

    # 可选临时导出目录：默认 <本脚本目录>/<PSD文件名>/；可填相对或绝对路径。
    # 完成后整个目录移动到 Laya 资源父目录下，预制体仍使用 PSD 文件名。
    # --output         "商城_给程序"

    # 可选诊断 JSON 路径：默认 <临时导出目录>/diagnostics.json。
    # 建议置于临时导出目录中，随结果一起移动到 Laya 工程。
    # --report         "商城_给程序/diagnostics.json"

    # 可选开关：严格导出，遇到无法完整支持的 PSD 内容时按严格规则报错。
    # --strict

    # 可选开关：忽略缓存，强制重新解析和导出 PSD；不填时复用有效缓存。
    # --reexport
)

# 复杂逻辑在 Python 中；命令行追加的同名参数覆盖上面的配置。
exec python3 "$(dirname -- "$0")/src/psd2ui/run_export.py" "${args[@]}" "$@"
