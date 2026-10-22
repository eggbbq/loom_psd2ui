# PSD2UI V1

直接读取 PSD / PSB，输出 PNG + `layout.json`，再生成 LayaAir **3.4.1** 原生 `.lh` 预制体。当前 Laya 工程直接引用预制体，panel 层级在 IDE 中可编辑，运行时不读取布局 JSON。Python 3.11+；不安装、不启动、不调用 Photoshop。原始导出协议依据 [开发规格](PSD2UI_V1_Codex_Development_Spec.md)，原生预制体是后续追加的功能。

完整操作见 [使用手册](使用手册.md)。

`test.psd` 使用 Git LFS 保存。首次克隆后，请安装 [Git LFS](https://git-lfs.com/)，运行 `git lfs install` 和 `git lfs pull`，确保下载到完整 PSD 后再执行导出。

## 导出并移入 Laya 工程（macOS / Linux）

```bash
./run_export.sh
PSD2UI_REEXPORT=1 ./run_export.sh  # 强制重新导出
```

脚本自动准备 Python 环境，读取参数数组中 `--input` 指定的 PSD，先导出到仓库根目录下的同名文件夹，成功后整体 `mv` 到 `laya-project/assets/ui/<PSD 文件名>/`。当前配置为 `商城_给程序.psd`，最终位置：

```text
psd2ui/laya-project/assets/ui/商城_给程序/
├── 商城_给程序.lh
├── 商城_给程序.lh.meta
├── layout.json
├── diagnostics.json
└── PSD 分组目录/…PNG 与 .png.meta
```

PNG 与预制体共用一套资源，目录按 PSD 分组结构保存，没有额外的 `assets` 层。预制体文件名取 PSD 文件名（不含扩展名）。`run_export.sh` 最后移动整个目录到 Laya 工程，保留已有 `.meta`，重复运行不会嵌套同名目录。它不修改场景、工程设置，不构建或启动浏览器；无需安装 LayaAir CLI。首次安装 Python 依赖需要网络。

`run_export.sh` 只保留 `args=(...)` 参数配置和对 `run_export.py` 的调用，环境准备、缓存、导出、生成预制体及移动目录均由 `run_export.py` 实现。`--flat-assets` 取消 `assets` 层，`--dedupe-images 0.99` 启用去重，注释去重行可关闭。修改参数、源 PSD、导出代码，或检测到布局被外部改写、图片缺失时，会自动重新导出；缓存保存在输出目录的 `.start-export.json` 中。

可以在命令行覆盖参数，或直接使用 Python 入口。相对路径均基于仓库目录：

```bash
./run_export.sh --input test.psd --reexport
./run_export.sh --help
python3 run_export.py --input test.psd --dedupe-images 0.99
```

在 IDE 中打开 `assets/ui/商城_给程序/商城_给程序.lh` 即可编辑。需要放入预览场景时，可手动拖入，或使用下面的同步脚本。

## 目录批量九宫格处理

`run_9grid.sh` / `run_9grid.py` 是独立入口，不会启动 PSD 导出。修改 sh 中 `--search-dir` 配置即可递归处理目录内全部 PNG；默认生成优化资源、通过引擎验证后回写 Laya，再检查资源完整性。

```bash
./run_9grid.sh --search-dir assets/ui --dry-run  # 项目零写入预演
./run_9grid.sh --search-dir assets/ui            # 完整执行
./run_9grid.sh --search-dir assets/ui --build-only  # 仅生成 PNG 和参数
```

搜索路径以 `--project` 指定的 Laya 工程为基准，默认工程为 `laya-project`。**输入、输出目录相同会自动原地写回 PNG，保留路径与 UUID；不同目录则另存优化图。** 原地写回先备份和验证，支持撤销。sh 已配置视觉近似模式，允许预算内的少量像素变化；加 `--mode strict` 切回严格无损。Python / 底层 CLI 的默认模式仍为 strict。每张图都会被检查，不满足当前模式条件的图按原因跳过。详细参数、跳过规则与撤销方式见 [九宫格使用说明](ninegrid/README.md)。

## 安装与转换

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

psd2ui export test.psd --output out/test --report out/test/diagnostics.json
psd2ui export test.psd --output out/test --dedupe-images 0.99  # 可选图片去重
python -m psd2ui export test.psd --output out/test --strict --report out/test/diagnostics.json
```

Windows 使用 `py -3 -m venv .venv` 和 `.venv\Scripts\Activate.ps1`，之后命令相同。Linux/macOS 使用以上命令。依赖由 pip 安装；导出阶段不需要网络。

退出码 `0` 表示完整导出成功；结构、合成、路径、文件写入错误返回 `1`。普通模式允许带有明确保真警告的可用输出；`--strict` 遇到保真、样式或空层警告返回 `1`，仍保留有效输出便于检查。`DUPLICATE_ASSET_PATH` 按需求覆盖，严格模式也仅提示。

诊断报告是 JSON 数组，每项有 `code`、`severity`、`psdPath`、`message`。终端同步打印。合成先在临时目录完成、验证 PNG 引用后再发布 `layout.json`；渲染失败不会发布半份场景。重复导出覆盖对应资源；启用去重时会删除本轮识别出的重复 PNG（含上次导出留下的同路径 PNG），其他历史文件不自动清理。需要干净交付时使用新的输出目录。

### 图片去重（可选）

导出命令增加 `--dedupe-images X`，`X` 是 `[0, 1]` 内的相似度阈值，默认关闭；`1` 只合并 RGBA 完全相同的图片。例如 `--dedupe-images 0.99` 允许每个像素的每个通道最多相差 2。Python API 对应 `export_psd(source, output, dedupe_images=0.99)`。

在 PNG 合成、透明外边校正、同路径覆盖及布局计算完成后，按最终 `layout.json` 的深度优先顺序遍历 image 节点，包含隐藏节点和 GLoader 图片。只比较宽、高都相等的图片，解码成 8 位 RGBA 后计算：`相似度 = 1 - max(|A[p,c] - B[p,c]|) / 255`，其中 `p` 遍历所有像素，`c` 遍历 R/G/B/A。透明像素的 RGB 也参与比较；去重步骤不缩放、不另行裁剪、不使用平均差值。

满足阈值时引用最早保留的节点资源，更新所有同路径引用，并删除重复 PNG。节点名称、位置、尺寸、类型、可见性和层级不变；原生预制体生成器会自然复用同一纹理。相似性不传递：若 B 已合并到 A，后续 C 只和保留的 A 比较，避免连续合并使差异超过阈值。未被本轮 layout 引用的其他文件不参与比较或删除。启用去重不会增加严格模式警告。

`test.psd` 在透明外边校正及 `0.99` 去重阈值下，496 张资源减少到 164 张，删除 332 张重复 PNG，502 个图片节点全部保留。结果见 [去重布局](out/test/layout.json)、[重复导出验证](out/validation/export.json) 和 [图片边界复核记录](out/validation/png-bounds.json)。重复导出结果一致，源 PSD 未变；生成的预制体引用 164 张纹理。

```bash
python scripts/validate_export.py --output out/test-dedup \
  --validation out/validation/dedup --dedupe-images 0.99
```

## 命名与输出

下面示例为导出 CLI 默认路径；`run_export.sh` 启用 `--flat-assets`，会移除路径开头的 `assets/`。

```text
PSD 图层面板（上 → 下）                 输出
ShopPanel                              layout.json
  img_Close  分组                      assets/ShopPanel/Close.png
    Icon                               （整体合成，不展开）
    #Reference                         （排除）
  Title       文本                      （JSON text，无 PNG）
  Background  图片                      assets/ShopPanel/Background.png
Settings      隐藏分组                  assets/Settings/Background.png
  Background  可见图片                  （节点均保留，本层可见性不变）
```

- 原始名称任意位置有 `#`，整个子树不导出，优先级最高。
- 名称以 `_` 分隔，第一段为类型，不使用 `$`。例如 `btn_settings_close` → 类型 `GButton`、名称 `settings_close`。New UI 类型名不区分大小写，未知前缀原样保留。`img_` 标在文本上时显式导出 PNG；旧 `$btn_`、`[img]`、`[image]` 等写法不再作为指令。
- 兼容旧 PSD 的 `.img` 标记：名称任意位置包含 `.img`（不区分大小写）时强制使用 `GImage`，优先于其他类型前缀；导出名移除该标记。例如 `组 9.img 拷贝` → `组 9 拷贝`，`btn_Close.img` → 名为 `Close` 的 `GImage`。分组整体合成单张 PNG，内部节点不再导出；`#` 排除规则仍优先。
- 没有 `_` 时用完整名称匹配类型，并保留原名，例如 `Button` → 名为 `Button` 的 `GButton`、`icon` → 名为 `icon` 的 `GLoader`。匹配不到时按 PSD 图层类别回退：分组 → `GWidget`，文本 → `GTextField`，图片 → `GImage`。
- 使用 LayaAir **New UI**：无标签分组 → `GWidget`，普通文本 → `GTextField`，普通图片 → `GImage`。`hbox_` / `vbox_` → `GBox` 横向 / 纵向布局；`panel_` / `pnl_` → `GPanel`，`button_` / `btn_` → `GButton`，`list_` → `GList`，`loader_` / `icon_` / `ico_` → `GLoader`，`progressbar_` / `bar_` → `GProgressBar`。`vhox_` 保留为 `vbox_` 别名。其他 `类型名_` 自动匹配 New UI 的 G 类型，例如 `combobox_` / `gcombobox_` → `GComboBox`。
- 文本缩写 `txt_` / `text_` / `title_` → `GTextField`；`input_` → `GTextInput`；`img_` → `GImage`，`pnl_` → `GPanel`，`icon_` / `ico_` → `GLoader`。例如 `title_player_name` 的导出名为 `player_name`。
- 中文类型别名：`背景` / `边框` / `图片` / `花边` / `底板` → image（`GImage`），`按钮` → button（`GButton`），`标题` → title（`GTextField`），`图标` → icon（`GLoader`）。完整名称与 `_` 前缀两种规则均适用，例如 `背景`、`按钮_确认`；图片类分组整体导出单张 PNG，不展开内部节点。
- 文本图层未匹配到类型，或移除类型前缀后的名称不是有效的 TypeScript 变量名时，强制命名为 `text`；处于 `GButton` / `GProgressBar` 内部（含嵌套分组）时改为 `title`。匹配类型且变量名合法时保留名称。按原始名称校验，不能靠路径字符替换把非法名字变成合法；保留字不合法，Unicode 标识符合法。多个文本回退同名时不添加编号。该规则仅修改名称，不修改文字、样式或位置，也不修改原 PSD。
- `img_` 分组只输出一张 PNG；排除内部 `#` 子树和隐藏子层。忽略整体自身的隐藏状态生成素材，节点仍保留 `visible: false`。
- 分组匹配 `icon` / `image` 类型时也强制整体导出图片：例如 `icon`、`icon_头像`、`image`、`image_背景`。只输出一个 image 节点和一张 PNG，内部图层、文字、嵌套分组不产生独立 JSON 节点或 PNG；预制体中也不展开内部层级。`icon` 对应 `GLoader`，`image` 对应 `GImage`。
- **分组自身有已启用的图层样式（描边、外发光、阴影、颜色叠加等）时，自动按整体图片导出，无须命名 `img_`。** 生成一张同组名 PNG，组内文字也烘焙进整体图片，不展开内部节点或输出各子层 PNG；若分组带按钮等类型标签，则在对应组件下保留一个整体图片子节点。过滤、隐藏状态和透明度规则与 `img_` 分组相同。
- **分组自身存在像素蒙版或矢量蒙版时，也强制整体合成图片**，把蒙版应用到整个组再导出，内部节点不再单独输出。默认使用 `GImage`；显式按钮等组件保留外层和单个合成图片子节点。停用的蒙版仍触发整体导出，但合成时遵循其停用状态；剪贴蒙版不是这一规则的触发条件。
- 特效总开关关闭、所有效果都禁用时，不触发自动合成。只在子图层或子组上设置效果，不会使无效果的祖先组一起压平；仅设置普通混合模式也不触发此规则。无法保真的效果仍有诊断，严格模式失败。
- 普通隐藏图层仍导出；没有启用效果且未标 `img_` 的分组保留层级。独立顶层分组就是 panel。
- 空分组不导出：没有子节点、递归只含空分组，或子节点均被 `#` 排除时，不生成 layout 节点、PNG、目录或预制体节点；类型前缀、图层样式也不会保留空分组。普通隐藏分组有可导出内容时仍保留。
- 组名对应目录，图层名对应文件名。中文、空格保留；路径分隔符、非法字符、`..`、Windows 保留名做安全规范化。空名称报错。规范化冲突和同名都按底 → 顶遍历顺序后写覆盖，不加后缀。
- 同路径覆盖后，所有引用使用最后 PNG；相关节点的 `size` 及裁剪偏移同步为最终 PNG 的值，位置按各节点原始合成原点加最终 PNG 裁剪偏移计算，父容器边界重新计算。

零尺寸空像素层无法编码成 PNG。本实现将这类有明确零尺寸记录的图层保留为 `container` 空节点、`size: [0,0]`，输出 `EMPTY_LAYER` 警告，严格模式失败。这是对空像素层的显式处理；不伪造 1×1 图片。不可信的非空边界、不可渲染的非空图层会报错。

## JSON 与坐标

```json
{
  "version": 1,
  "name": "ui",
  "type": "root",
  "position": [0, 0],
  "size": [750, 1624],
  "visible": true,
  "children": [
    {
      "type": "image",
      "name": "Background",
      "position": [10, 20],
      "size": [100, 80],
      "visible": true,
      "asset": "assets/Background.png"
    }
  ]
}
```

坐标单位是 PSD 像素，左上为原点；节点相对直接父节点。容器边界取实际导出子节点并集，包含隐藏节点；不使用库的可见层 group bbox。合成时为描边预留临时画布，输出时按 alpha 非零边界裁掉完全透明的外边，同时补偿图片绝对原点，再计算父容器和子节点局部坐标。PNG 与节点尺寸一致，内容在文档中的位置不变。即使 alpha 只有 1/255 也保留；全透明 PNG 保留原尺寸，避免生成 0×0 图片。不对矢量坐标或宽高强制取整，不重采样图片。此规则消除 PSD 缓存与临时画布造成的额外留白；库仍可能无法准确渲染 Photoshop 的部分效果，见诊断。

本次对真实 PSD 的 502 个图片节点逐一对比修正前后的像素和绝对位置：270 个节点去除了透明外边，所有可见 RGBA 像素保持一致，229 个可编辑文本的绝对位置保持不变；84 个列表 `bg_item` 统一输出 100×100。详见 [边界复核记录](out/validation/png-bounds.json)。

`children` 永远底 → 顶排列。锁定的 psd-tools 迭代已经是该顺序，不额外反转。图片自身透明度烘焙一次；普通容器与文本的 `opacity` 由引擎应用。

文本包含可读取的 `text`、`font`、`fontSize`、`color`、`align`、`outline`、`outlineColor`、`shadow`、`shadowColor`、`shadowBlur`。换行转为 `\n`，文本空间字号乘以 PSD transform 的垂直缩放得到像素字号。缺失字段不填造，报告 `UNREADABLE_TEXT_STYLE`；多样式文本使用首个有效样式并报告 `UNSUPPORTED_RICH_TEXT`。详细类型见 [types.ts](runtimes/layaair3/types.ts)。

文本的位置/尺寸使用 PSD 文本排版 `bounds` 经 `transform` 转换后的矩形，而非缓存像素的 `layer.bbox`（字形边界）；否则字体自身留白会再次计入，导致偏移。缺失排版框时回退字形边界并报告 `UNREADABLE_TEXT_BOUNDS`，严格模式失败。`状态栏/头像/Lv 10` 已有实际引擎像素回归：文本框原点 `[36,104]`，最终字形边界 `[39,116,119,138]` 与 PSD 相同。

## LayaAir 原生预制体

`run_export.sh` 已在生成预制体后移入 Laya 工程。仅重新生成预制体及 `.meta`，无需再次解析 PSD：

```bash
.venv/bin/python scripts/generate_asset_bundle.py laya-project/assets/ui/商城_给程序/layout.json
```

需要同步到本仓库示例工程时，显式执行：

```bash
.venv/bin/python scripts/sync_laya_project.py --source-output laya-project/assets/ui/商城_给程序
```

同步输出为 `laya-project/assets/psd2ui/商城_给程序/商城_给程序.lh`，PNG 保持 layout 中的相对目录；同时更新 `assets/Scene.ls` 的预制体引用及 `PlayerSettings.resolution.designWidth/designHeight`，保留其他工程设置、已有资源 UUID、场景实例覆盖属性和手工添加的实例节点。

使用 LayaAir IDE **3.4.1** 打开 [PSD2UIDemo.laya](laya-project/PSD2UIDemo.laya)，打开同步后的同名 `.lh` 编辑节点，运行 `assets/Scene.ls` 预览。重新生成会覆盖生成的预制体内容，手工编辑前请另存副本。

通用脚本也可指定其他目标工程、预制体和场景：

```bash
.venv/bin/python scripts/generate_laya_prefab.py laya-project/assets/ui/商城_给程序/layout.json \
  --project laya-project \
  --output assets/PSD2UI/商城_给程序.lh \
  --scene assets/Scene.ls
```

省略 `--output` 时使用 `assets/PSD2UI/<PSD 文件名>.lh`；省略 `--scene` 不改场景。通用脚本将纹理复制到预制体同名子目录，不修改设计分辨率。需要保持独立导出的平铺结构时，使用整目录复制或上面的同步脚本。

根节点及无标签分组使用 `Laya.GWidget`，文本使用 `Laya.GTextField`，图片使用 `Laya.GImage`。图片默认使用 `GImage.src`（`autoSize: false`）引用 PNG，`loader_` / `icon_` / `ico_` 使用 `GLoader.src`。目标工程启用 `laya.ui`，并配置 `addons: {"laya.ui": "ui2"}`，示例工程已经选择 New UI。文本显式设置零 padding，保留已验证的 PSD 文字位置。位置、尺寸、可见性、alpha、文本样式和子节点顺序直接写入 `.lh`，运行时不读取 JSON、不动态创建 panel。

特殊组件在 JSON 中记录 `component`（如 `GButton`）。`hbox_道具栏` 导出为名为 `道具栏` 的 `GBox`，JSON `layout: "horizontal"`；`vbox_` 对应 `"vertical"`。按 PSD 的 x / y 排列直接子节点，用相邻边界差计算 `gap`，写入原生 `layout.columnGap` / `rowGap`。隐藏子节点也参与，空组或单子节点为 0，重叠时允许负间距。原始间距不一致时取平均值并报告 `NON_UNIFORM_LAYOUT_GAP`；New UI 使用统一间距重新排列。普通组保持底 → 顶顺序，只有显式 HBox/VBox 按布局轴排序。

图片类型的分组合成一张 PNG。按钮等类型标在普通单层上时，生成对应组件并保留一个原始图片 / 文本子节点；带图层特效的类型分组也用单个合成图片子节点保持外观。列表模板、按钮状态、进度条绑定等交互属性可在 IDE 中设置，生成器不推测绑定。生成前检查路径、PNG 和尺寸，输入错误时不覆盖已有预制体；同步场景时保留实例覆盖属性及手工添加的节点。

完整操作见 [原生工程说明](laya-project/README.md)。当前测试 PSD 生成 1,062 个节点、502 个图片节点（未去重 496 张 PNG，边界校正及阈值 0.99 去重后 164 张）和 229 个文本节点，已经通过 CLI 资源校验、Web 构建及浏览器逐节点验证；浏览器测试明确断言运行中没有请求 `layout.json`。

## 独立 Loader 示例（可选）

`runtimes/layaair3/example` 保留早期的 Sprite/Text JSON Loader 示例供独立集成使用。当前 `laya-project` 和 `run_export.sh` 使用上面的 New UI 静态预制体流程。

使用实际 LayaAir **3.4.1** 的运行库和 `LayaAir.d.ts` 编译验证。其他 3.x 版本尚未验证，不能保证 API 相同。引擎准备脚本会检查版本；本次验证的文件哈希记录在 [engine-lock.json](runtimes/layaair3/engine-lock.json)。引擎源码可从 [LayaAir 官方仓库](https://github.com/layabox/LayaAir) 获取，构建产物需要有 `build/libs`、`build/types`。也可使用本机已有的相同版本源码构建目录：

```bash
# 从项目根目录运行，替换成自己的引擎路径
python scripts/prepare_laya.py /path/to/LayaAir-3.4.1

cd runtimes/layaair3
npm ci
npm run typecheck
npm run build
cd ../..
python -m http.server 8765 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8765/runtimes/layaair3/example/>，默认加载 `out/test/layout.json`。引擎文件复制到本地 `example/vendor/`，随附原 MIT License，不提交到版本控制。示例代码和 Loader 可直接集成到已有 3.4.1 工程：

```typescript
import { PsdUiLoader } from "./PsdUiLoader";

// Laya.init() 之后；字体先安装/注册完成
const scene = await PsdUiLoader.load("/ui/layout.json", {
    assetRoot: "/ui/",       // 默认 layout.json 所在目录；需包含 JSON 中的 assets/ 路径
    panelName: "ShopPanel", // 可省略，省略时导入全部顶层节点
    onWarning: console.warn,
});
Laya.stage.addChild(scene);
```

panelName 只能选同名的唯一顶层 container；缺失或同名歧义报错。保留 panel 原位置、可见性。隐藏 panel 也完整实例化，调用方可以之后显式显示。按 JSON 顺序逐项添加、设置递增 `zOrder`，纹理加载完成后才返回。缺少 PNG 会拒绝 Promise，并销毁创建中的节点。不会自动生成按钮交互或 IDE `.ls/.lh`。

字体由应用负责提供。Loader 每种 PSD 字体发出一次提示；浏览器字体回退、行高、字形基线和 Photoshop 排版差异会改变外观。先加载字体再实例化；普通文本始终保留为引擎 Text，不以 PNG 替代。

## 测试与实际交付

```bash
pytest -q
python -m psd2ui export tests/fixtures/rules.psd --output out/rules --strict --report out/rules/diagnostics.json
python scripts/validate_export.py  # 真实 test.psd 重复导出、逐资源哈希、严格模式和源文件不变验证

# 先完成引擎准备、npm ci、typecheck 和 build，再运行真实浏览器集成测试
cd runtimes/layaair3
npm test
npm run test:native  # 先构建 laya-project，验证原生预制体及零 layout.json 请求
```

集成测试默认使用已安装的 Chrome，无需启动 IDE。也可运行 `npx playwright install chromium` 后设置 `PLAYWRIGHT_CHANNEL=chromium`。测试自行启动临时 HTTP 服务，结束后释放。真实用户 PSD 需预先导出到 `out/test`。

可共享的 [rules.psd](tests/fixtures/rules.psd) 是真实可读取的多图层 PSD，包含双 panel、多级组、隐藏层、普通文本、文本栅格缓存、`img_` 组、`#` 子树、三色叠放；可运行 `python -m tests.fixture_factory` 重建，不依赖 Adobe。用户的 `test.psd` 覆盖大量智能对象、形状和真实复杂效果。

验收覆盖：

| 规格 | 验证 |
|---|---|
| T01–T06 | 像素 RGBA、目录与相对坐标、`#` 排除、隐藏层及本层可见性 |
| T07 | 同名不同尺寸后写覆盖、PNG 与全部 JSON 引用尺寸一致、严格模式允许覆盖 |
| T08–T13 | 普通文本样式与无 PNG、显式 `img_` 图片/文本、组内排除、隐藏整体、单次透明度 |
| T14 | 真实 LayaAir 3.4.1 GPU 渲染回读，红/绿/蓝三层交叠像素断言 |
| T15 | 实际引擎选择隐藏 panel，验证后代仍在、未绕过可见性 |
| T16–T19 | 路径安全/符号链接、不可读样式与严格退出码、独立 PSD/PSB 读取、全部资产存在/尺寸验证 |
| T20 | 两个 CLI 入口重复导出，JSON 和 PNG SHA-256 一致 |

另外覆盖合成失败不发布场景、可见性状态恢复、缺失 panel/PNG 明确失败。实际引擎测试递归比较用户 PSD 的全部运行节点名称、位置、尺寸、可见性与子序列；不能将这些结构测试当作 Photoshop 像素级保真的证明。

本次实际结果：

- [用户 PSD 场景](out/test/layout.json)、[诊断](out/test/diagnostics.json)、[图片目录](out/test/assets/)。750×1624；33 个顶层节点；502 个 image 引用，未去重使用 496 张 PNG，边界校正及阈值 0.99 去重后使用 164 张；229 个 text；330 个 container（其中 3 个为空像素层）。重复使用输出目录可能保留以前不再引用的 PNG。
- [LayaAir 浏览器截图](out/test/layaair-preview.png)、[引擎原尺寸透明背景渲染](out/test/layaair-render.png)、[PSD 内嵌合成预览](out/test/psd-embedded-preview.png)。最后一项只供对照，导出器不使用整图预览代替分层解析。透明背景显示方式随查看器不同。
- [规则样例输出](out/rules/layout.json)、[真实 PSD 导出验证](out/validation/export.json)、[原生预制体验证](out/validation/native-project.json)。Python 自动测试覆盖 New UI 前缀、自动间隔、分组效果整体导出、文本排版框及 transform 的回归测试。浏览器另外通过真实 PSD 标签样例验证 New UI 类型、GLoader 图片及 GBox 自动间隔。

## 已知视觉限制

psd-tools 不等于 Photoshop 渲染器。当前锁定 `psd-tools[composite]==1.17.4`，使用其分层像素缓存及合成能力；不自行实现 Photoshop 渲染系统。官方说明见 [使用文档](https://psd-tools.readthedocs.io/en/latest/usage.html) 和 [图层 API](https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.api.layers.html)。

- 智能对象、矢量形状使用缓存/库的有限绘制；不保证重新编辑后的复杂内部内容一致。
- 调整层、非普通混合、剪贴蒙版、穿透组、组蒙版、图层效果逐层报告 `UNSUPPORTED_VISUAL_EFFECT`。带已启用效果的分组自动整体合成，仍受库渲染能力限制；其他复杂结构可按需标 `img_`。
- 库的阴影、光晕、外扩描边等渲染存在缺失或截断；不会因成功生成 PNG 就声称支持。文本描边/阴影参数尽力提取，实际绘制是 LayaAir 的近似效果；渐变描边、叠加颜色、特定混合也可能不同。
- 字体、文本基线/行距、非等比缩放、旋转、多样式 run 不保证精确重现。图片透明度只烘焙一次，容器 alpha 对重叠子项的效果仍可能与 PSD 的隔离合成不同。
- CMYK/LAB/高位深文件输出会转换为 8 位 RGBA 并警告；不保证印刷色彩匹配。
- 用户样例包含大量上述效果、7 处多样式文本、6 次同名路径覆盖。因此普通导出可用，严格导出应失败，画面有明确记录的差异；完整视觉保真验收未通过。

PSD 导出器本身未接入九宫格、Atlas、压缩或响应式布局；九宫格优化通过上面的独立入口运行。
