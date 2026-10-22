# PSD2UI LayaAir 示例工程

使用官方 **LayaAir 3.4.1「2D empty project」模板**创建，启动场景直接引用从 `layout.json` 编译出的原生 `.lh` 预制体。

## 在 IDE 打开

1. 启动 LayaAir IDE **3.4.1**，选择「打开本地项目」。
2. 选择本目录 `laya-project`，或打开其中的 **`PSD2UIDemo.laya`**。
3. 打开 `assets/PSD2UI/test.lh`，在层级面板中查看、编辑 panel、图片和文本。
4. 打开 `assets/Scene.ls`，点击 IDE 的「运行 / 预览」按钮。

当前所有 1,062 个节点（含根节点）都已写入 `test.lh`，纹理为原生 UUID 资源引用。带已启用图层效果的 PSD 分组已整体导出成图片；其内部不再生成独立节点。启动场景通过 `_$prefab` 引用此资源，无动态 Loader 组件，运行时不读取 `layout.json`。

当前工程使用 **LayaAir New UI**（`addons.laya.ui = "ui2"`）。无标签分组及根节点为 `GWidget`，文本为 `GTextField`，图片为 `GImage`，文本 padding 为 0。

| PSD 前缀 | 原生类型 |
|---|---|
| `hbox_` | `GBox`，横向布局 |
| `vbox_` / `vhox_` | `GBox`，纵向布局 |
| `panel_` / `pnl_` | `GPanel` |
| `button_` / `btn_` | `GButton` |
| `list_` | `GList` |
| `loader_` / `icon_` / `ico_` | `GLoader` |
| `progressbar_` / `bar_` | `GProgressBar` |
| `img_` / `image_` | `GImage`，分组整体导出图片 |
| `txt_` / `text_` / `title_` | `GTextField` |
| `input_` | `GTextInput` |
| `背景` / `边框` / `图片` / `花边` / `底板` | `GImage` |
| `按钮` | `GButton` |
| `标题` | `GTextField` |
| `图标` | `GLoader` |

名称以 `_` 分隔，第一段为类型，不使用 `$`。其他 `类型名_` 自动匹配 New UI G 类型，允许带 G 的完整名称，例如 `gbutton_`。类型名不区分大小写，未知前缀保留；例如 `btn_settings_close` 的导出名是 `settings_close`。旧 `$btn_`、`[img]`、`[image]` 不再作为指令。

中文别名同样支持完整名称和前缀，例如 `背景` → `GImage`（保留名称），`按钮_确认` → `GButton`（名称 `确认`）。图片、图标类的分组强制整体生成一张 PNG，不展开内部节点。

没有 `_` 时直接用完整名称匹配，例如 `Button` → `GButton`、`txt` → `GTextField`、`icon` / `ico` → `GLoader`，节点名保留原名。没有匹配时，按图层类别生成 `GWidget`（分组）、`GTextField`（文本）、`GImage`（图片）。

文本图层未匹配到类型，或移除前缀后的名称不是合法 TypeScript 变量名时，强制使用 `text`；在按钮、进度条内部（包括嵌套分组）使用 `title`。例如 `Lv 10` → `text`，`txt_123` → `text`，`btn_确认` 内的未命名类型文本 → `title`；`txt_player_name` 则保留 `player_name`。文字内容及坐标保持。回退名称不自动加编号。

匹配 `icon` / `image`（含 `ico` / `img` 别名）的分组强制整体合成一张 PNG，只生成一个 `GLoader` / `GImage`，不展开内部图层、文本或嵌套分组。

HBox/VBox 按 PSD 子节点的 x/y 排序，从相邻边界推算间距并写入 `columnGap` / `rowGap`。间距不一致时使用平均值并产生诊断；空组、单节点间距为 0，隐藏节点参与计算。其他控件可在 IDE 中配置按钮状态、列表模板、进度条绑定等。带效果的类型分组仅保留一个合成图片子节点。

可见性按 PSD 保留，因此大部分隐藏 panel 初始不可见。要查看某个隐藏 panel，可在预制体层级中选中它并修改 `visible`；也可把该 panel 拖出、另存为独立预制体。生成脚本按输入重新覆盖预制体内容，手工修改需要保留时请另存副本。

```text
laya-project/
├── PSD2UIDemo.laya           # IDE 工程入口，版本 3.4.1
├── assets/Scene.ls           # 放置原生预制体实例的启动场景
├── assets/PSD2UI/test.lh     # 可编辑的完整 PSD UI 层级
├── assets/PSD2UI/test.lh.meta
├── assets/PSD2UI/test/assets/ # 边界校正及去重后引用 164 张 PNG（未去重 496 张），使用稳定 UUID 的 .meta
├── src/Main.ts              # 可选空脚本，启动场景未挂载
├── engine/types/            # 官方 CLI 随模板生成的引擎声明
└── settings/                # 启动场景、750×1624 画布、Web 构建配置
```

PNG 位于 IDE 的 assets 目录，以稳定 UUID 引用。`GImage` / `GLoader` 通过 `src` 引用 PNG。宽高使用布局数据，`GImage.autoSize` 关闭。PSD 图片不生成 Atlas、九宫格或压缩资源；New UI 默认皮肤可能由构建器打入内置图集。`copyBinFiles` 已关闭，旧版 bin 布局数据不参与构建。

导出合成后自动裁去完全透明的外边，图片坐标补偿裁剪偏移；容器尺寸和局部坐标同步计算，内容在文档中的位置不变。半透明的抗锯齿和效果像素保留。同路径覆盖时，所有引用使用最终 PNG 的尺寸和裁剪偏移。

## 更新 PSD 数据

在上一级 PSD2UI 根目录执行：

```bash
.venv/bin/python -m psd2ui export test.psd --output out/test --report out/test/diagnostics.json
.venv/bin/python scripts/generate_laya_prefab.py out/test/layout.json \
  --project laya-project --output assets/PSD2UI/test.lh --scene assets/Scene.ls
```

也可以运行 `.venv/bin/python scripts/sync_laya_project.py`，它会按默认路径重新生成预制体并更新场景引用。已有纹理/预制体 UUID 保留；场景实例的覆盖属性和手工添加的节点保留。相同输入生成的子节点 ID、顺序和路径稳定。位置、尺寸、可见性、文本、描边与阴影均直接序列化。生成前校验 PNG 和尺寸；源数据错误时不覆盖之前的资源。使用父项目 Python 虚拟环境。

生成到其他工程时，修改 `--project` 和 `--output`；输出必须位于该工程 `assets` 下且扩展名为 `.lh`。不传 `--scene` 时只生成资源，不修改场景。字体仍由运行环境提供。

## CLI 验证与运行

从本目录执行（需要已安装 LayaAir CLI 3.4.1）：

```bash
layaair validate assets/PSD2UI/test.lh assets/Scene.ls --skip-package-install
layaair run --skip-package-install
```

`run` 会打印预览地址，按 `Ctrl+C` 停止。按需构建 Web：

```bash
layaair build web --skip-package-install
```

产物为 `release/web/`，通过 HTTP 服务访问其 `index.html`。不要双击 HTML 使用 `file://` 打开。

从父目录执行 `./start.sh` 也会生成预制体、构建原生工程并打开浏览器。脚本顶部 `args=(...)` 集中配置导出参数，默认 `--dedupe-images 0.99`；完整操作见 [使用手册](../使用手册.md)。已通过 CLI 校验及实际 3.4.1 Web 构建验证，递归核对 1,062 个节点的位置、尺寸、可见性、子节点顺序、文字和纹理；浏览器验证运行中没有请求 `layout.json`。记录见父目录 `out/validation/native-project.json`。

复杂图层效果、组描边、字体排版的现有限制沿用导出器诊断；详情见父项目 README 及 `out/test/diagnostics.json`。

