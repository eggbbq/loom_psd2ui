# PSD2UI V1 — Codex 开发规格（无 Photoshop 依赖）

> 状态：V1 实施基线  
> 日期：2026-10-21  
> 目标：直接用 Python 读取 PSD，遵循极少量命名规则，导出 PNG + `layout.json`，由 LayaAir 3.x 按 PSD 的图层结构还原 UI。  
> 最高优先级：**实现简单、结构直观、尽量所见即所得。**

---

## 0. Codex 执行指令

请按本文件实现一个可运行的最小闭环，不要只搭建目录或生成伪代码。

1. 实现跨平台 Python CLI，**不要求电脑安装、启动或调用 Adobe Photoshop**。
2. 解析 PSD/PSB 的图层、分组及基本文本属性，导出 `layout.json` 和 PNG。
3. 实现 LayaAir 3.x TypeScript 端的最小 UI Loader，使用 JSON + PNG 在运行时还原 UI；**不需要生成 LayaAir IDE 原生 `.ls/.lh` 文件**。
4. 编写单元测试、至少一个含真实图层结构的 PSD 测试样例和 README；运行测试并展示实际导出结果。
5. 先完成完整可用的 V1，再考虑扩展。**禁止提前实现九宫格、Atlas、压缩、性能优化或 AI 识别。** 相似图合并现已按后续需求加入可选参数，见 6.3；透明外边校正按后续 1px 留白问题修正实现，见 4.2。
6. 对第三方库不能准确解析或合成的 Photoshop 特性，报告明确的 warning/error；不允许默默忽略并声称 100% 视觉一致。

本规格中，用户的命名与导出规则（原 R1～R8 及追加 R9）属于**确定要求**；为消除歧义补充的实现约定见第 3～6 节。若样例与文字冲突，以第 2～6 节的规则为准。

## 1. 项目范围与技术选型

### 1.1 唯一目标

```
PSD / PSB（无需 Photoshop）
    ↓ Python exporter
layout.json + PNG
    ↓ LayaAir JSON Loader
开发期 UI（位置、结构、可见性、外观尽量与 PSD 一致）
```

### 1.2 建议技术

- Python 3.11+；`psd-tools` 读取 PSD 图层树、文本与图层合成能力；`Pillow` 输出 RGBA PNG。
- 推荐试用 `psd-tools[composite]` 以提高部分图层效果支持度，**但不得将其视为 Photoshop 的完全兼容渲染器**。
- `pytest` 测试；`argparse` 实现 CLI，避免 GUI 和重量级依赖。
- 引擎端：LayaAir 3.x + TypeScript（轻量 JSON Loader）。
- PSD、PSB 文件通过磁盘路径直接读取；禁止使用 Photoshop COM、ExtendScript、UXP、AppleScript、自动点击 Photoshop 或先手工导出素材等方案。

资料：
- https://github.com/psd-tools/psd-tools
- https://psd-tools.readthedocs.io/en/latest/usage.html
- https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.api.layers.html

## 2. 用户确认的导出规则（不得擅改）

| # | 规则 | 程序行为 |
|---|---|---|
| R1 | **名称含 `#` 的图层/分组不导出** | 任意位置含 `#` 都排除；若为分组，整个子树排除。 |
| R2 | **同一 PSD 中不同 panel 必须通过分组管理** | 由 PSD 分组表达 panel 边界。转换器不靠图像分析猜 panel。 |
| R3 | **非 `#` 图层无论隐藏与否都必须导出** | 不按 `visible` 过滤；保留原始 `visible` 值，由引擎决定显示。 |
| R4 | **图片输出目录与文件名对应 PSD 分组、图层命名，同名直接覆盖** | 逐级文件夹与组名相同；PNG 文件名来自图层名。相同目标路径后写覆盖先写。 |
| R5 | **文本不导出图片** | 一般文本图层生成 JSON `text` 节点及文字属性，不导出 PNG。 |
| R6 | **名称以 `img_` 开头的图层或分组作为整体图片输出** | 单个 image 节点 + 单张 PNG；`img_` 分组不再展开子节点。 |
| R7 | **JSON 是场景树；相对 PSD 图层面板的视觉排序反转** | JSON 每个 `children` 数组按**底层 → 顶层**存储，后一个节点覆盖在前一个节点之上。 |
| R8 | **节点使用简单 JSON 属性** | 节点至少包含 `type`、`name`、`position`、`visible`，图片有路径，文本有颜色、字号、描边、阴影等可提取参数。 |
| R9 | **分组自身使用描边、外发光等已启用图层样式时，作为整体图片导出** | 无需 `img_` 标记，输出单个 image 节点和单张 PNG，不展开其子节点；包括组内文字在内的可见内容整体合成。 |
| R10 | **第一段类型映射 New UI** | 以 `_` 分隔，不使用 `$`：`hbox_` / `vbox_` → `GBox` 横向 / 纵向布局；`panel_` / `pnl_` → `GPanel`，`button_` / `btn_` → `GButton`，`list_` → `GList`，`loader_` / `icon_` / `ico_` → `GLoader`，`progressbar_` / `bar_` → `GProgressBar`。其他名称自动匹配 New UI G 类型；无标签分组为 `GWidget`，文本为 `GTextField`，图片为 `GImage`。 |

## 3. 具体命名与解析约定

### 3.1 `#` 优先级最高

- 对**原始 PSD 名称**先检查 `#`，命中则完全跳过该图层/分组及所有后代。
- `#` 与 `img_` 同时存在时仍然跳过。
- 例如 `#参考图`、`bg#备份`、`img_Panel#` 都不导出。

### 3.2 `img_` 是显式“合成一张图片”指令

- 名称以 `_` 分隔，第一段为类型，类型名不区分大小写，不使用 `$`。例如 `img_MainBg` → 类型 `GImage`、名称 `MainBg`，`btn_settings_close` → `GButton`、名称 `settings_close`。未知前缀保留；旧 `$img_`、`[img]`、`[image]` 不再触发合成。
- 没有 `_` 时以完整名称匹配类型，节点名保留原名，例如 `Button` → `GButton`、`txt` → `GTextField`、`icon` / `ico` → `GLoader`。未知类型按 PSD 图层类别回退为 GWidget（分组）、GTextField（文本）、GImage（图片）。
- 特殊规则：分组匹配 icon / image 类型（包括 ico / img 别名）时，强制整体合成单张 PNG，JSON 仅一个 image 节点，预制体仅一个 GLoader / GImage。内部的图层、文字及嵌套分组均不生成独立节点或 PNG。完整名称与首段类型两种匹配方式均适用。
- 从导出的节点名、文件夹名中去掉 `img_` 后再做路径安全处理：`img_MainBg` → `MainBg`。
- 非文本普通像素图层即使不带 `img_`，也导出为 image 节点；`img_` 对普通图层可视为显式确认。
- **`img_` 分组是关键特殊情况**：将组内符合规则的可见内容合成一张 PNG，导出一个 image 节点，不再导出组内各子图层的 JSON 节点或 PNG。
- **明确的优先级约定**：`img_` 标记在文本图层时，按显式指令导出 PNG，优先于 R5 的普通文本规则。这是 R5/R6 同时命中的唯一特例。
- `img_` 合成分组时，内部 `#` 子树必须排除；不能直接使用会把 `#` 内容混入的原始合成预览。
- **R9 自动整体合成**：检查分组自身的图层效果总开关及各效果的启用状态。至少一个效果启用时，按与 `img_` 分组相同的规则整体导出；保留组名，组内文字也合成进 PNG。总开关关闭或全部效果禁用时不触发；只有后代有特效时，不把无效果的祖先组一起压平。普通混合模式本身不触发此规则。

### 3.3 隐藏层与 `img_` 的交互

- 对普通图层/分组，不论是否隐藏，**均导出节点及可用 PNG**，`visible` 保留其 PSD 当前状态（本层状态，而非与父层合并后的最终状态）。
- 对于**隐藏的 `img_` 整体**，仍生成 PNG，JSON 节点 `visible: false`。导出合成图时临时忽略**整体节点自身**的隐藏状态。
- `img_` 分组里的**隐藏子图层**默认不参与合成（保持 PSD 当前组内的可见外观）；它们不产生独立节点，因为整个组已被有意压成一个 image 节点。
- 这是“隐藏层仍导出”与“`img_` 组必须整体压平”之间的必要边界：**R3 对每个独立输出节点生效；`img_` 组内部不产生独立输出节点。**
- R9 自动整体导出的分组遵循本节相同规则，包括 `#` 排除、本组隐藏时仍生成图片、隐藏子层不参与合成和透明度只烘焙一次。
- 若 psd-tools 无法按上述可见性与排除规则合成，报错或警告并停止该节点生成，不能静默导出错误图像。

### 3.4 Panel 组织

- 同一 PSD 的不同界面仍可用独立顶层分组区分，`panel_` / `pnl_` 指定 `GPanel`，允许嵌套。未匹配到类型时，分组生成 `GWidget`，文字生成 `GTextField`，图片生成 `GImage`。
- JSON `component` 使用 New UI 类名。支持省略 G，例如 `button_` / `gbutton_` → `GButton`；`btn_`、`icon_` 等别名按 R10。未知前缀保留，已识别前缀从名称和路径中移除。
- 缩写 `txt` / `text` / `title` → `GTextField`，`input` → `GTextInput`，`img` → `GImage`，`pnl` → `GPanel`，`icon` / `ico` → `GLoader`。文本类型保持可编辑的文本节点，不导出 PNG。
- 中文别名：背景、边框、图片、花边、底板 → image（GImage）；按钮 → button（GButton）；标题 → title（GTextField）；图标 → icon（GLoader）。完整名称匹配与 `_` 分隔的首段匹配均适用，继承对应类型的图片整体合成、按钮内文本命名等规则。
- 文本图层的类型未匹配，或移除类型前缀后的原始名称不是合法 TypeScript 变量名时，节点强制命名 `text`；在 GButton 或 GProgressBar 内部（包括经过普通嵌套分组）使用 `title`。命中类型且变量名合法时保留名称。保留字不合法，Unicode 标识符合法，不通过路径规范化规避变量名检查。文字、样式、坐标与原 PSD 不变，回退名称不加自动编号。显式图片类型的文本图层仍沿用图片导出规则，只应用同样的名称回退。
- `hbox_` / `vbox_` 分别生成 `component: "GBox"`、`layout: "horizontal"` / `"vertical"`；`vhox_` 为纵向别名。直接子节点按 x/y 排序，相邻边界差的平均值写入 `gap`，转换为 `columnGap` / `rowGap`。空组或单子节点间距 0；隐藏节点参与，负值表示重叠。间距不一致时报告 `NON_UNIFORM_LAYOUT_GAP`。仅显式线性布局允许改变子节点顺序，其余组仍按底 → 顶顺序。
- `loader_` / `icon_` / `ico_` 分组合成一张图片并写入 `GLoader.src`。按钮等类型的单层或带效果分组，在对应组件下放置一个图片/文字子节点以保留外观；带效果分组的后代不再展开。普通图片及 `img_` / `image_` 使用 `GImage.src`（autoSize 关闭）。按钮状态、列表模板、进度条绑定等在 IDE 配置。
- 整个 PSD 只生成一个 `layout.json`；JSON 根的子节点包括这些顶层 panel。LayaAir Loader 可以通过顶层分组名选择性实例化 panel。
- 顶层若还有普通图层，也作为根节点子项导出，不自动推断其 panel 归属；项目内应尽量避免歧义。
- 不允许通过扁平化层级实现 panel 划分。

### 3.5 名称与文件路径

- 输出文件夹路径来自**当前 image 节点的普通祖先分组**；普通分组生成文件夹。`img_` 分组自身输出 PNG，不为其子项生成文件夹。
- 原始名称去掉已识别的特殊前缀后用于 `name`；不要自动改成 `btn_`、`img_` 等语义名称。
- 路径分隔符、`..`、系统非法字符等必须进行最小安全规范化，防止路径穿越；中文、空格等合法字符尽量保留。
- 如果规范化后名称为空，产生明确错误，不要生成匿名文件。
- **同一路径同名后写覆盖先写**，按确定的导出遍历顺序执行，不自动加 `_1`、`_2`；`layout.json` 里相关节点都引用最终相同路径。
- 覆盖可能导致同名但内容不同的图片最终显示一致，这是 R4 的显式要求；CLI 在此情形打印 `DUPLICATE_ASSET_PATH` 警告，便于美术调整命名。
- 仅同一父目录中的同名文件发生覆盖；不同组中可有同名图片，例如 `ShopPanel/icon.png`、`SettingPanel/icon.png`。

## 4. 位置、层级、尺寸的统一规则

### 4.1 坐标

- 左上角是原点 `(0, 0)`，X 向右，Y 向下；单位为 PSD 像素，不做缩放。
- 根场景原点为 PSD 画布左上角；场景 `size = [PSD.width, PSD.height]`。
- 每个节点 `position = [x, y]`，**相对于直接父节点**。
- 普通文本节点使用 PSD 文字排版 `bounds` 经文本 `transform` 转换到文档坐标后的矩形；不得直接以 `layer.bbox` 或 `boundingBox` 的字形像素边界作为文本框原点，以免字体留白重复计算。排版框缺失或无效时可明确警告后回退字形边界；`--strict` 失败。
- 普通分组的节点原点取其**实际导出子项边界的并集左上角**；子节点坐标据此转换，允许负偏移。
- image 节点的 `position` 必须与导出的 PNG 的**有效图像边界**一致（包含渲染时实际扩张的效果范围）。图片 `size` 与其 PNG 物理尺寸一致。后续边界修正：合成阶段保留描边检测所需的临时画布，合成后按 alpha 非零边界裁去完全透明的外边，将裁剪偏移加回图片文档坐标，再计算父子局部坐标；不缩放、不强制取整矢量几何，保留所有 alpha > 0 的抗锯齿和效果像素。全透明图片保留原非零画布，不生成 0×0 PNG。图片去重在边界校正后执行。
- 对仅包含隐藏层的分组，仍须计算可导出子节点的几何边界，不能简单依赖“只含可见层”的 PSD group bbox。
- 若无法得到某个节点可信的几何边界，记录详细错误，不要无提示地把它放在 `(0,0)`。

### 4.2 绘制顺序（R7）

- **JSON 唯一规定的顺序：`children[0]` 最底层，最后一个最顶层。**
- Photoshop 图层面板通常以“上方显示在上层”的顺序展示；因此视觉上对应其反序。
- **切勿不经验证地把 `psd-tools` 迭代结果再反转一次**：库的 API 顺序不一定等于 Photoshop 面板顺序。应通过官方迭代语义/测试 PSD 验证，最终输出只满足上述 JSON 的绘制次序。
- 这个顺序规则对根、Panel、任意嵌套分组均生效。

### 4.3 可见性、透明度与特效

后续新增规则：分组存在像素蒙版或矢量蒙版时，强制整体输出单张 PNG，合成时应用分组蒙版及其启用状态；内部节点不再独立输出。若显式指定按钮等容器类型，保留组件外层和一个合成图片子节点。兼容旧资源名称中的 `.img` 标记（不区分大小写），强制映射 `GImage`、整体导出分组，并移除导出名中的 `.img`；优先于普通类型前缀，低于 `#` 排除规则。

- `visible` 是本节点原始可见状态；若父容器 `visible=false`，引擎的层级可见性自然使所有后代隐藏，但后代数据仍在 JSON。
- 尽量保持视觉一致，不要对同一个图层的透明度既写入 PNG alpha 又写成引擎 `alpha` 导致**重复衰减**。
- 对不压平的普通分组，尽量把组透明度存为容器 `opacity`；图片若已将自身 opacity 烘焙进 PNG，JSON 不再次应用同一透明度。
- PSD 的剪贴蒙版、复杂混合模式、调整图层、智能对象、图层效果、组穿透模式等可能无法由独立普通 image 节点准确还原。**V1 不开发复杂 Photoshop 渲染引擎**；至少生成 `UNSUPPORTED_VISUAL_EFFECT` 诊断，不允许无声失真。可建议美术对这些结构手工标 `img_` 后重新导出，但仍受库合成能力限制。

## 5. `layout.json` V1 协议

只使用一棵递归树，避免过早设计复杂引擎抽象。V1 节点类型：`root`、`container`、`image`、`text`。

### 5.1 顶层格式

```json
{
  "version": 1,
  "name": "game_ui",
  "type": "root",
  "position": [0, 0],
  "size": [1080, 1920],
  "visible": true,
  "children": []
}
```

字段约定：

| 字段 | 适用节点 | 说明 |
|---|---|---|
| `type` | 全部 | `root` / `container` / `image` / `text` |
| `name` | 全部 | 移除已识别特殊前缀后的 PSD 名称 |
| `component` | 非 root 节点 | 可选的 New UI G 类型；分组缺省 GWidget，文本缺省 GTextField，图片缺省 GImage |
| `layout` / `gap` | `container` | 可选，horizontal / vertical 及自动计算的统一间距 |
| `position` | 全部 | `[x, y]`，相对父节点左上角，像素 |
| `size` | 全部 | `[width, height]`，像素 |
| `visible` | 全部 | 原始本层是否可见；隐藏层也有节点 |
| `children` | `root`, `container` | 子节点，按底 → 顶绘制顺序排列 |
| `asset` | `image` | 相对 `layout.json` 的 PNG 路径，使用 `/` 分隔符 |
| `text` | `text` | 文本内容；PSD 换行转换为 `\n` |
| `font` | `text` | PSD 中可读的字体名称 |
| `fontSize` | `text` | PSD 中可读字号，单位 px（必要时转换单位） |
| `color` | `text` | `#RRGGBB` 或 `#RRGGBBAA` |
| `align` | `text` | `left` / `center` / `right`，缺失用 `left` |
| `outline` | `text` | 可读取的描边像素宽度，未设置为 `0` |
| `outlineColor` | `text` | 可读取的描边颜色 |
| `shadow` | `text` | `[offsetX, offsetY]`；未设置时省略 |
| `shadowColor` | `text` | 可读取的阴影颜色 |
| `shadowBlur` | `text` | 可读取的模糊半径，若无法解析则省略并警告 |
| `opacity` | `container`, `text` | 可选，0~1；仅在未被素材预先烘焙时应用 |

避免为了“看起来完整”填造不存在或不可读取的样式。无法获取颜色、字号等关键字段时，报告诊断；CLI `--strict` 模式下退出非 0。复杂多样式文本 V1 不要求还原为多个富文本 run，需报告 `UNSUPPORTED_RICH_TEXT`。

### 5.2 示例 PSD 与 JSON

PSD 图层面板示意（**从上到下**）：

```text
ShopPanel                          [group, visible]
  #美术参考                           [group, ignored]
  img_CloseButton                [group, visible]
    icon                            [pixel]
    glow                            [pixel]
  标题                               [text, visible]
  Background                        [pixel, visible]
SettingPanel                       [group, hidden]
  Title                             [text, visible]
  Background                        [pixel, visible]
```

输出结构：

```text
output/
├── layout.json
└── assets/
    ├── ShopPanel/
    │   ├── Background.png
    │   └── CloseButton.png
    └── SettingPanel/
        └── Background.png
```

> `img_CloseButton` 是整体图片，所以没有 `CloseButton/` 子目录，也没有 `icon.png`、`glow.png`；普通文字 `标题`、`Title` 不生成 PNG。

```json
{
  "version": 1,
  "name": "game_ui",
  "type": "root",
  "position": [0, 0],
  "size": [1080, 1920],
  "visible": true,
  "children": [
    {
      "type": "container",
      "name": "SettingPanel",
      "position": [100, 100],
      "size": [880, 1600],
      "visible": false,
      "children": [
        {
          "type": "image",
          "name": "Background",
          "position": [0, 0],
          "size": [880, 1600],
          "visible": true,
          "asset": "assets/SettingPanel/Background.png"
        },
        {
          "type": "text",
          "name": "Title",
          "position": [200, 60],
          "size": [300, 60],
          "visible": true,
          "text": "设置",
          "font": "Arial",
          "fontSize": 48,
          "color": "#00FFFF",
          "align": "center",
          "outline": 2,
          "outlineColor": "#000000",
          "shadow": [-1, -1],
          "shadowColor": "#000000"
        }
      ]
    },
    {
      "type": "container",
      "name": "ShopPanel",
      "position": [100, 100],
      "size": [880, 1600],
      "visible": true,
      "children": [
        {
          "type": "image",
          "name": "Background",
          "position": [0, 0],
          "size": [880, 1600],
          "visible": true,
          "asset": "assets/ShopPanel/Background.png"
        },
        {
          "type": "text",
          "name": "标题",
          "position": [200, 60],
          "size": [300, 60],
          "visible": true,
          "text": "商店",
          "font": "Arial",
          "fontSize": 48,
          "color": "#00FFFF",
          "align": "center",
          "outline": 0
        },
        {
          "type": "image",
          "name": "CloseButton",
          "position": [800, 16],
          "size": [64, 64],
          "visible": true,
          "asset": "assets/ShopPanel/CloseButton.png"
        }
      ]
    }
  ]
}
```

上述数值是**协议示例**，不代表可从任意 PSD 中无损提取。实际转换必须从源文件读取真实值。

## 6. Python 导出器详细行为

### 6.1 推荐的处理顺序

1. 读取 PSD 文档元信息：尺寸、色彩模式、图层树。
2. 递归扫描原始图层，按 R1 过滤 `#`，解析 `img_` 指令；**不要因隐藏而跳过**。
3. 对带已启用图层效果的分组（R9）、`img_` 组及图片图层构造 `image`；其余普通组构造 `container` 并继续递归，普通文本构造 `text`。
4. 计算所有保留节点的 PSD 绝对像素边界；形成可靠的父子相对 `position`。
5. 校正每一级子节点的底 → 顶绘制顺序。
6. 保存需导出的 PNG，组路径与 PSD 一致；有同名则覆盖并打印警告。
7. 生成 JSON；验证所有 image 节点引用的 PNG 确实存在，并且 `size` 与 PNG 像素尺寸相符。
8. 输出日志/诊断汇总（无需另做 UI）。

### 6.2 关于 Photoshop 独立性

- `PSDImage.open(path)` 直接读取磁盘 PSD，不需要 Photoshop 可执行文件，也不得尝试后台启动 Photoshop。
- 文本数据使用 `TypeLayer.text`、`typesetting` / `engine_dict` / `resource_dict` 等读取可获得的属性。
- 图片数据使用 psd-tools 提供的像素/合成接口，并由 Pillow 写成 RGBA PNG。
- **禁止声称任何复杂 PSD 都能 100% 保真**：psd-tools 不等于 Photoshop 渲染引擎，尤其字体绘制与某些图层效果存在限制。
- 若无法在不调用 Photoshop 的情况下还原某特殊图层，保留明确的可追踪诊断并在 README 中说明；不要偷偷截图 Photoshop 或强迫人工逐层导出。

### 6.3 CLI

```bash
# 安装
python -m pip install -e '.[dev]'

# 转换一个 PSD/PSB
psd2ui export ./ui.psd --output ./out/ui

# 严格模式：不支持的关键元素或缺失关键数据导致非 0 退出
psd2ui export ./ui.psd --output ./out/ui --strict

# 列出转换警告（或写入可供 CI 使用的 diagnostics.json）
psd2ui export ./ui.psd --output ./out/ui --report ./out/ui/diagnostics.json

# 后续新增：可选图片去重（默认关闭，1 为完全相同）
psd2ui export ./ui.psd --output ./out/ui --dedupe-images 0.99
```

同样接受：`python -m psd2ui export ...`。参数名与行为按上述实现，不能只有内部 Python 函数而没有 CLI。

图片去重阈值 `X` 必须为 `[0,1]` 内的有限数。遍历最终 layout 的 image 节点（深度优先，含隐藏节点），读取实际引用 PNG，只比较宽高均相等的图片。相似度定义为 `1 - max(abs(a-b)) / 255`，最大值覆盖每个像素及 RGBA 每个通道（含透明像素 RGB）；相似度 `>= X` 时改用首个保留节点的资源，删除本轮重复 PNG，保留所有节点及其他属性。只与保留资源比较，不进行传递合并。去重发生在最终同路径覆盖之后、layout 发布之前；不删除无关历史文件，不修改源 PSD，严格模式允许显式启用去重。

### 6.4 诊断格式

至少具备：`code`、`severity`、`psdPath`（层级路径）、`message`。

建议覆盖：
- `DUPLICATE_ASSET_PATH`
- `UNSUPPORTED_VISUAL_EFFECT`
- `UNSUPPORTED_RICH_TEXT`
- `UNREADABLE_TEXT_STYLE`
- `INVALID_EXPORT_NAME`
- `COMPOSITE_FAILED`
- `MISSING_ASSET`
- `INVALID_BOUNDS`

### 6.5 失败策略

- 结构性错误（PSD 不可读、导出目录不可写、图片无法导出、路径越界、JSON 引用失效）必须非 0 退出。
- 无法完全保真的效果，普通模式记录警告并尽最大可能输出；`--strict` 下视为失败。
- 不要输出缺文件却声称成功的 `layout.json`。
- 同名覆盖是用户指定行为；仅警告，不默认视为失败。

## 7. LayaAir 3.x TypeScript Loader

### 7.1 职责

- 输入：`layout.json` URL + PNG 资源根目录，可选 `panelName`。
- `root` / `container` → 具备子节点的容器；`image` → Image/Sprite；`text` → Text/Label（按目标版本实际 API 选择）。
- 设置名称、可见性、相对位置、尺寸、文本、字体/大小/颜色、描边、阴影等该 LayaAir 版本支持的属性。
- 按 `children` 数组顺序添加子节点，确保**后加入的节点绘制在上层**；若引擎版本有其他规则，使用可测试的 z-order 映射。
- `panelName` 指定时从根节点选取同名顶层分组；未指定时按全部根子节点导入。
- 不需要九宫格、不需要 atlas、不需要打包资源处理、不需要 PSD 解析代码移植进引擎。
- 引擎兼容必须用项目锁定的实际 LayaAir 3.x 版本验证，不得假设所有 3.x API 完全相同。

### 7.2 边界

- V1 只做**运行时/预览端 JSON UI 实例化**。自动生成 IDE 可编辑的 `.ls/.lh` 文件属于后续需求，当前不实现。
- 文本字体要由运行环境提供；若字体未安装或游戏未打包，文本可有偏差，Loader 应有字体缺失提示或 README 说明。
- Loader 不能绕过 `visible: false`，也不得把父容器隐藏导致的子元素丢弃。

## 8. 项目结构（建议）

```text
psd2ui/
├── pyproject.toml
├── README.md
├── src/psd2ui/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── psd_reader.py
│   ├── naming.py
│   ├── layout_builder.py
│   ├── image_exporter.py
│   └── diagnostics.py
├── runtimes/layaair3/
│   ├── PsdUiLoader.ts
│   ├── types.ts
│   └── example/               # 最小可运行示例/集成说明
└── tests/
    ├── test_naming.py
    ├── test_layout.py
    ├── test_export.py
    └── fixtures/              # 可共享的 PSD/PSB 测试素材
```

具体模块可根据实现调整，不要为架构形式过度拆分。

## 9. V1 必须通过的验收测试

| 编号 | 测试场景 | 预期结果 |
|---|---|---|
| T01 | 普通像素图层 | 正确 PNG、image 节点、尺寸、位置 |
| T02 | 多级分组 | 目录路径正确，JSON 递归父子坐标正确 |
| T03 | 名称含 `#` 的图层 | 不导出任何节点和 PNG |
| T04 | 名称含 `#` 的分组 | 整个子树不导出 |
| T05 | 隐藏图层 | 仍生成 PNG/节点，`visible=false` |
| T06 | 隐藏分组与子图层 | 组/子图层均保留，按各自可见性还原 |
| T07 | 同父目录同名图片 | 最终文件由后写覆盖；不自动改名；输出警告 |
| T08 | 普通文本图层 | 不生成 PNG；JSON 包含原文和可读的样式属性 |
| T09 | `img_` 普通图层 | 生成一张图片及一个 image 节点 |
| T10 | `img_` 分组 | 只生成一张合成 PNG 和一个 image 节点，不输出内部节点 |
| T11 | `img_` 组内有 `#` | 被排除内容不得混入合成图 |
| T12 | 隐藏 `img_` 组 | 生成可用 PNG，但 JSON `visible=false` |
| T13 | 文本图层命名带 `img_` | 显式图片导出，符合优先级约定；如不可合成给出清晰诊断 |
| T14 | 叠放顺序 | 重叠三层的实际引擎画面与 PSD 上下遮挡一致 |
| T15 | 同 PSD 两个 panel | 顶层独立分组，能通过 Loader 指定 `panelName` |
| T16 | 路径非法字符/`..` | 不发生目录穿越；命名冲突有明确信息 |
| T17 | 无法解析的文字样式 | 明确警告；strict 模式退出非 0 |
| T18 | 完全不安装 Photoshop 的环境 | `export` 与测试均可运行，不依赖 PS 进程 |
| T19 | PNG 相对路径验证 | 每个 `asset` 文件存在；尺寸匹配 |
| T20 | 重复执行导出 | 生成稳定顺序/文件路径/结构（同样输入同样结果） |
| T21 | 未命名 `img_` 的分组带已启用描边/外发光 | 生成单个 image 节点与同组名 PNG，不单独导出组内子层或文字 |
| T22 | 特效总开关关闭或所有效果禁用 | 不自动压平，保留普通 container 层级 |
| T23 | 自动合成组含隐藏层、`#` 子树，或自身隐藏 | 排除 `#` 与隐藏子层；整体隐藏状态保留，仍生成可用 PNG；透明度只应用一次 |

建议真实 PSD 验收样本至少包括：多级组、隐藏层、文本、`img_` 组、`#` 排除层、两个 panel、重叠遮挡。另留一个含复杂特效的 PSD 专门测试正确诊断，而不强行追求无损支持。

## 10. Codex 交付清单与完成标准

- [ ] `psd2ui` Python 包及可用 CLI；macOS/Windows/Linux 不依赖 Photoshop。
- [ ] 输入真实 PSD，可生成正确目录的 PNG、`layout.json`。
- [ ] 用户 R1～R8 与第 3～6 节的优先级、坐标、顺序约定一致。
- [ ] LayaAir 3.x 示例工程或可集成 Loader，可显示至少一个 panel。
- [ ] `README.md`：安装、命令、PSD 命名示例、JSON 结构、已知限制。
- [ ] 自动化测试（至少 T01～T20 中可在项目测试环境运行的部分），说明尚缺的真实 PSD 样例。
- [ ] 运行测试并提供结果，附一份实际导出的 `layout.json`、图片目录和 diagnostics 示例。
- [ ] 若无法真实验证 LayaAir 端，明确标注“未完成集成验证”，不以 Python 测试通过代替完整验收。

### 明确不做（V1 禁止扩大范围）

- 图像九宫格检测/压缩；Atlas、纹理编码、性能调优。相似图片去重按后续需求作为显式可选功能实现，见 6.3。
- 依靠 AI 识别按钮或组件、根据截图推断 UI 结构。
- Photoshop 插件、Photoshop 批处理、PS 脚本自动化。
- 自动将图层转换为交互按钮、富文本编辑器、布局约束系统或响应式 UI。
- LayaAir 原生场景格式序列化或 Cocos Creator 适配。

---

## 11. 需注意的技术事实（不要误报已支持）

1. `psd-tools` **可以不依赖 Photoshop 读取 PSD/PSB 的图层、像素、文本及部分样式**，这符合本项目的硬性要求。
2. `psd-tools` **不是完整的 Photoshop 渲染器**：复杂图层效果、图像调整、某些混合与字体排版、矢量内容、智能对象都可能无法与 Photoshop 完全一致。
3. 普通文本转引擎文本也无法在未携带字体及等效排版引擎时保证像素级一致。V1 应尽力提取并报告差异，不能因这一事实擅自把普通文本全部转 PNG（R5）。
4. `img_` 遇到文本和复杂效果也可能无法由 Python 完全重绘；应明确失败或降级诊断，而不是调用 Photoshop。
5. **可验证的正确行为比貌似成功的输出更重要**：路径、坐标、节点树、PNG 资产与可见性必须准确；视觉特性若不受支持，应当可识别。

---

**Codex 结束条件：** 真实 PSD → Python 导出 `layout.json + PNG` → LayaAir 显示 UI 的完整演示闭环运行成功，且全部核心规则有测试覆盖；没有开发任何发布阶段图像优化功能。
