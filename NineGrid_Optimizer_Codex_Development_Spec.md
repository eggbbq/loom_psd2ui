# NineGrid Optimizer — 自动九宫格纹理面积优化与 LayaAir 项目回写

> **Codex 开发规格 · V1.0 · 2026-10-22**  
> **技术路线**：Python 3.11+ / NumPy / Pillow；LayaAir 3.x 项目集成  
> **工作范围只有一个**：从已有 PNG 自动发现可无损收缩的重复区域 → 生成较小 PNG 与九宫格参数 → **真实写回 LayaAir 项目中的资源引用与九宫格配置** → 自动验证。  
> **明确不做**：PSD 解析、图层命名、UI 场景生成、文字转换、相似图片合并、Atlas、其他纹理压缩、AI 视觉模型、改变已有 UI 布局。

## 1. 目标、边界与验收定义

### 1.1 目标

一张原本 `600×300` 的 UI 面板 PNG，如果水平与垂直方向分别存在能够无损重复扩展的像素带（例如四边各 16 px，中间分别可收缩为 1 px），程序生成 `33×33` 的优化 PNG，并为引用该图片的 LayaAir Image 节点配置正确的 `skin` 和 `sizeGrid`；节点的目标显示宽高仍为 `600×300`，位置、父子关系、可见性、透明度等均不变。

像素面积节省率为 `1 - 33×33/(600×300) ≈ 99.395%`。**该指标是源纹理像素面积节省，不等于文件字节数或 DrawCall 的同比下降**。

### 1.2 最高优先级

1. **安全**：不能错误替换纹理；所有写回应能预览、撤销并重复执行。
2. **无损优先**：第一版仅识别像素完全重复的连续行/列，不使用近似相似度、插值拟合或 AI 猜测。
3. **真正接入项目**：必须更新项目中实际使用该图片的 UI 节点或经确认有效的纹理资源属性，不能只输出 `sizeGrid` 报告。
4. **保留原图**：默认生成新图并改引用，不覆盖原始素材。
5. **独立性**：只依赖磁盘 PNG 与 LayaAir 项目；不依赖 Photoshop，也不需要前序任何转换程序。

### 1.3 验收完成的定义

- 对可优化样例，自动生成尺寸更小的 PNG，算法能从该 PNG 在原始尺寸还原出 **RGBA 完全一致** 的图像（先通过 Python 像素级测试）。
- 对不可优化样例，保持不动并给出明确原因。
- 在提供的**真实 LayaAir 3.x 测试项目**中，完成 `skin`/`sizeGrid` 回写，重新打开或运行项目后正确显示，原 UI 布局和外观不发生明显变化。
- `--dry-run` 零写入；正式写入有备份/清单/撤销；重复运行不产生重复资产、不反复缩图。
- 至少有一项 LayaAir 实际渲染前后截图对比测试，不能仅凭 Python 模拟宣布“与引擎一致”。

---

## 2. 输入与输出

### 2.1 输入

- 已存在的 PNG 文件或 PNG 目录。
- 指定的 LayaAir 3.x 项目根目录（内含实际的 UI 场景/预制体/纹理资源），供关联资源与回写。
- 可选：资源扫描根目录、允许的场景目录、最小节省阈值、输出目录。

### 2.2 输出目录示例（相对于 LayaAir 项目根目录）

```text
GameProject/
├── assets/
│   ├── ui/shop/panel.png                 # 原图：保留
│   ├── ui/shop/other.png
│   ├── ninegrid_auto/ui/shop/panel.png   # 自动生成：例如 33×33
│   └── scenes/Shop.ls                    # 引用和 sizeGrid 已安全回写
└── .ninegrid/
    ├── manifest.json                     # 原图/新图/参数/引用/哈希
    ├── report.json                       # 本次优化结果、跳过原因
    ├── report.md
    └── backups/<run-id>/                 # 被修改项目文件的原始副本
```

具体 `assets` 目录及场景文件的位置以实际项目结构为准；不要假设所有 LayaAir 版本完全相同。

### 2.3 Manifest 数据协议（工具内部，独立于 LayaAir 的序列化格式）

```json
{
  "schemaVersion": 1,
  "items": [
    {
      "source": "assets/ui/shop/panel.png",
      "sourceSha256": "<实际计算值>",
      "sourceSize": [600, 300],
      "output": "assets/ninegrid_auto/ui/shop/panel.png",
      "outputSha256": "<实际计算值>",
      "outputSize": [33, 33],
      "sizeGrid": {
        "top": 16,
        "right": 16,
        "bottom": 16,
        "left": 16,
        "repeat": 0
      },
      "layaSizeGrid": "16,16,16,16,0",
      "removedColumns": {"start": 16, "length": 568},
      "removedRows": {"start": 16, "length": 268},
      "pixelAreaSavedRatio": 0.99395,
      "status": "optimized",
      "references": [
        {
          "file": "assets/scenes/Shop.ls",
          "nodeId": "<从实际场景读取的稳定标识>",
          "oldSkin": "assets/ui/shop/panel.png",
          "newSkin": "assets/ninegrid_auto/ui/shop/panel.png"
        }
      ]
    }
  ]
}
```

注意：以上是**优化器自己的 JSON**，**不是**声称 LayaAir `.ls` 文件就长这样。集成时必须适配并验证目标版本的原生格式。`sourceSha256` 必须用于幂等性与源文件变更检测。

---

## 3. 自动识别算法（严格无损版）

### 3.1 核心思路

不识别“按钮”“面板”等语义，而是寻找能够从原 PNG 删除、又能通过九宫格拉伸无损恢复的冗余像素带。

对于 RGBA 图片 `image[H, W, 4]`：

- 当两相邻整列所有 RGBA 像素相等，认为该列间可连续延伸。
- 当两相邻整行所有 RGBA 像素相等，认为该行间可连续延伸。
- 分别寻找最大的连续“全等列”区间和最大的连续“全等行”区间。
- 每个被选区间保留一行/一列，其余删除；它所在的位置决定九宫格左右/上下边距。
- 只有一维可压缩时允许只压缩一维；没有可压缩维度则跳过。

**不允许**基于平均色或仅比较中心区来判断：边框上的不同细节可能在九宫格拉伸时被破坏，必须比较跨越整张图片高度/宽度的像素向量。

### 3.2 可编码的定义

设原图宽度 `W`，连续相同列的最大候选区间为半开区间 `[a, b)`，包含 `r = b-a` 列，要求 `r >= 2`。

- 压缩后的图像保留原图 `[0,a+1)` 的全部列，以及 `[b,W)` 的全部列。
- 压缩后宽度 `W' = W-r+1`。
- 九宫格 `left = a`、`right = W-b`、水平中心区域宽度为 `1`。
- 只要 `W' > left+right`，即存在有效中心宽度，才算结构合法。

垂直方向设 `[c,d)`、`q=d-c`：

- 保留原图 `[0,c+1)` 的全部行，以及 `[d,H)` 的全部行。
- `H' = H-q+1`，`top=c`，`bottom=H-d`，垂直中心区域高度 `1`。

**重要**：如果没有该方向的可收缩区间，那么该维保持原始像素尺寸，九宫格对应两侧边距置 `0`，该维显示尺寸保持原尺寸；最终仍需通过 Laya 实际验证。若目标引擎对于零边距或极小中心纹理存在兼容性问题，跳过该候选，不要强行写回。

### 3.3 伪代码

```python
from PIL import Image
import numpy as np

rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
# shape = (height, width, 4)

same_adjacent_cols = np.all(rgba[:, 1:, :] == rgba[:, :-1, :], axis=(0, 2))
same_adjacent_rows = np.all(rgba[1:, :, :] == rgba[:-1, :, :], axis=(1, 2))

# 将连续 True 的边连接关系转换成连续全等行/列区间；
# 例如 k 个相邻 True 表示 k+1 个全等列。
# 搜索候选，并按节省面积排序。
# 每个候选必须完成重建验证才允许接受。
```

NumPy 可以降低大图遍历成本；算法必须避免不必要的整图重复复制。

### 3.4 候选选择与收益

- 候选从节省后像素面积最小者开始尝试，而不是仅凭边距大小决定。
- 默认 `min_area_saving_ratio = 0.20`（允许 CLI 调整）；低于阈值则跳过。
- 默认要求输出纹理宽/高至少为 `1`；如具体 Laya 版本存在限制，应将限制作为适配器能力配置，**不得在算法层悄悄改动数据**。
- 当全图是单一颜色时，可候选 `1×1` 纹理；需要明确测试该纹理在 Laya 原尺寸下的拉伸显示是否准确。若全零边距在对应版本无效，可作为普通拉伸纹理或跳过，不应伪称九宫格成功。
- 如果 PNG 的全透明像素 RGB 不同，V1 **不自动归一化透明 RGB**（避免过滤采样边缘风险）。
- 若图片本身存在动画状态拼接、多帧图、九宫格原有配置、特殊采样、旋转纹理引用等，默认跳过，除非有专门的测试覆盖。

### 3.5 为什么目前不做“渐变压缩”

渐变相邻像素不相等，把渐变缩成 1px 会丢失色彩变化。V1 应当跳过，后续即使引入近似压缩，也必须单独设计误差容忍度与引擎端视觉验收。本项目**不做**近似算法。

---

## 4. PNG 输出与像素级还原验证

### 4.1 输出规则

- 生成标准 RGBA PNG，保留各像素值和 alpha，不做颜色量化、调色板转换、缩放或有损编码。
- PNG 物理尺寸改变，但**Laya UI 节点显示尺寸完全不变**；不能给节点设置成新 PNG 的 `33×33`。
- 图像边缘的 alpha/颜色信息必须与原 PNG 一致；有纹理采样接缝时由引擎测试识别并拒绝候选。
- 输出路径具备稳定命名，不因第二次运行额外生成 `_optimized_2` 之类的链式压缩。

### 4.2 Python CPU 验证

编写 `reconstruct_9slice()`，给定 `optimized_png`、四边距和原尺寸，使用**确定性的九宫格最近邻复制规则**恢复到原尺寸，比较完整 RGBA 数组：

- `np.array_equal(original_rgba, reconstructed_rgba) == True` 才通过严格无损检测。
- 这项检测验证算法本身；**不能代替 GPU/Laya 的实际渲染验证**。
- 另外输出可选 diff 图片，失败时记录第一个错误像素坐标及不同像素数。
- CPU 还原器应单独针对单向收缩、双向收缩、边距为零、`1×1`、透明边缘等样例测试。

### 4.3 引擎视觉验证

在 LayaAir 实际项目中，分别渲染“优化前 UI”与“优化后 UI”，使用相同场景、分辨率、缩放模式、浏览器/设备、纹理过滤和采样设置：

- 先比较 PNG 本身的重建一致性，再比较实际截图。
- 默认要求关键案例截图像素严格一致；若 GPU/过滤造成微小差别，必须报告差异统计和截图，不得自动扩大容差并宣称无损。
- 遇到接缝/边缘伪影，应回退该图像的项目修改。
- 对多个不同实际使用尺寸分别验证；特别检查节点原本不是按 PNG 原尺寸显示时的情况。

---

## 5. LayaAir 项目回写：必须实现，不得停留在生成 JSON

### 5.1 引擎接口事实

LayaAir 3.x 的 `Image` 具有 `skin` 和 `sizeGrid` 属性；`sizeGrid` 格式为**字符串**：

```text
"top,right,bottom,left,repeat"
```

例如：`"16,16,16,16,0"`。最后一项 `0` 为拉伸（本项目默认），`1` 为重复平铺（V1 不启用）。`Image.width`、`Image.height` 保持优化前原值。

在 LayaAir 3.4 文档中，部分精灵纹理支持在纹理资源级配置九宫格，并被引用者继承；但**具体资源元数据结构与行为需要以用户的实际引擎版本和项目文件为准，不能臆造元数据 JSON 字段**。

### 5.2 集成默认方式：回写场景/预制体 Image 节点

Codex 需要实现 `LayaProjectAdapter`，分两步操作：

**A. 发现与解析**

1. 检测项目版本和目录结构；扫描项目里实际存在的 UI 场景/预制体，优先支持 `.ls` / `.lh`。
2. 从用户提供的**真实样例**中确认资源引用（路径、UUID 等）和 Image 属性的实际序列化方式。
3. 解析场景节点，建立 `skin/纹理资源 → 使用节点` 的反向引用表。
4. 忽略与该 PNG 无关的资源和节点，不改动节点层级与其他字段。
5. 仅支持已验证的场景序列化格式；遇到未知版本/格式直接拒绝写回，提供兼容性错误报告。

**B. 生成事务性补丁**

1. 对经验证可优化的 PNG，将新图复制到项目受控资源目录。
2. 对引用原图的合格 `Image` 节点，原位修改 `skin` 为新资源引用，同时设置 `sizeGrid` 为计算结果。
3. 保留节点的 `width`、`height`、`x`、`y`、`anchor`、`scale`、`visible`、`alpha`、`name`、子节点及其他原有属性。
4. 如果 `useSourceSize`、动态换肤、已有 `sizeGrid`、动画状态或其它配置与本操作冲突，则默认跳过此引用，不能强改。
5. 对同一 PNG 的多个引用分别校验；如有不安全引用，允许只替换安全引用，但**必须保留原 PNG**，且必须保证不会改动不安全引用。
6. 原图引用可能通过资源 UUID/元数据而不是简单字符串路径建立；实际回写应按项目资源引用机制创建新资源、维护元数据和引用一致性，不可仅盲目字符串替换。
7. 在提交前检查补丁目标文件可重新解析。备份被修改文件，然后通过临时文件+原子替换提交；中途失败应按备份回滚。
8. 输出每个修改的场景、节点、旧纹理、新纹理、旧九宫格、新九宫格、修改成功与否。

**完成条件**：LayaAir IDE 重新打开项目后，受影响节点仍能正常显示，并能在 Inspector 或实际运行时验证新纹理及 `sizeGrid` 生效。

### 5.3 备选集成方式：纹理资源级九宫格

如果该 LayaAir 版本的项目样例**明确验证**支持在 Sprite Texture 资源上设置并继承九宫格，则可以为专门生成的新图使用纹理元数据配置，并保留现有节点引用替换逻辑。此方式必须测试与节点自身 `sizeGrid` 的优先级关系。若不能确认版本格式，则**不采用**此方式。

### 5.4 运行时 UI 的特殊情况

如果目标项目并非使用 `.ls/.lh` 存储 Image，而是运行时 TS 代码动态生成 UI，那么不允许 Python 使用模糊正则乱改 TS 源码。可导出结构化的 `ninegrid-manifest.json` 供独立 TS 集成代码在创建节点时读取和设置，**但这属于补充路径，不能代替本项目对真实场景文件的回写验收**。

### 5.5 场景中不是按原图大小显示时怎么办？

九宫格和整图拉伸的视觉结果不一定相同。如果 Image 使用的目标尺寸不是原 PNG 的物理尺寸，默认 `skip`，或仅在对这一实际目标尺寸做过 Laya 截图验证后允许替换。不能仅因为 PNG 自身可以九宫格收缩就认定所有引用都安全。

---

## 6. CLI 设计

以模块形式运行，避免要求用户安装全局可执行文件：

```bash
# 仅分析：零改动，预览候选和节省量
python -m ninegrid scan --project ./GameProject --min-saving 0.20

# 生成优化 PNG + manifest + Python 还原验证；不写场景
python -m ninegrid build --project ./GameProject --output assets/ninegrid_auto

# 预演回写操作（列出将新增/修改的文件、节点、九宫格）
python -m ninegrid apply --project ./GameProject --dry-run

# 实际写回 LayaAir 项目（需要已完成 build）
python -m ninegrid apply --project ./GameProject

# 对当前 manifest 运行像素对比和项目引用完整性检查
python -m ninegrid verify --project ./GameProject

# 根据上一笔 apply 备份/事务清单进行回滚
python -m ninegrid rollback --project ./GameProject --run-id <run-id>
```

命令参数和默认输入/输出目录可根据项目实际调整，但必须保留等价的 `scan/build/apply/verify/rollback` 功能以及 `--dry-run`。`scan` 应能递归扫描子目录并以确定顺序输出结果。

安全要求：限制所有写入目录必须在指定项目根目录内；阻断 `..`、符号链接越界和目录穿越；严格匹配资源引用；缺少项目或无可解析场景时不得假称已写回。

---

## 7. 实现模块与工程建议

```text
ninegrid-optimizer/
├── pyproject.toml
├── README.md
├── ninegrid/
│   ├── __main__.py
│   ├── scan.py                  # RGBA 重复行/列检测
│   ├── candidate.py             # 候选裁剪方案选择、收益估算
│   ├── crop.py                  # 生成小尺寸 PNG
│   ├── reconstruct.py           # CPU 九宫格还原
│   ├── verify.py                # 严格像素对比
│   ├── manifest.py              # 版本化协议、哈希、报告
│   └── laya/
│       ├── project.py           # 版本/目录识别
│       ├── references.py        # 场景引用扫描
│       ├── adapter.py           # 实际场景序列化适配器
│       └── patch.py             # dry-run、备份、回滚、原子写入
├── tests/
│   ├── fixtures/png/
│   ├── fixtures/laya/          # 真实 IDE 样例，含原始和预期结果
│   ├── test_scan.py
│   ├── test_reconstruct.py
│   ├── test_manifest.py
│   └── test_laya_apply.py
└── docs/
    └── compatibility.md        # 已证实支持的具体 LayaAir 版本/文件格式
```

依赖：Python 3.11+、Pillow、NumPy、pytest。除测试或验证所需的 LayaAir 编辑器/运行环境外，实际 PNG 分析和裁剪不依赖引擎进程。

---

## 8. 必须实现的自动化测试

| 编号 | 样例 | 预期结果 |
|---|---|---|
| T01 | 纯色 RGBA 面板 | 识别可大幅收缩；Python 原尺寸还原全等 |
| T02 | 四角各异、四边重复、中间统一颜色 | 正确算出四边距；无损还原 |
| T03 | 只有水平可压缩 | 只收缩宽度；高度与原图相同 |
| T04 | 只有垂直可压缩 | 只收缩高度；宽度与原图相同 |
| T05 | 内有渐变/噪声 | 无严格重复区间则跳过 |
| T06 | 边缘半透明抗锯齿 | RGBA 全等比较，不能错误合并 |
| T07 | 完全透明但 RGB 不一致 | 不默认忽略隐含 RGB |
| T08 | 彩色复杂插画 | 未达到收益阈值则跳过 |
| T09 | 任意候选还原像素不一致 | 拒绝写回，原图不变 |
| T10 | 多个相同原图引用 | 只对安全引用修改，不能误改其他节点 |
| T11 | Image 存在尺寸缩放/已有 sizeGrid/动态皮肤 | 默认跳过并写清原因 |
| T12 | Laya 场景结构含未知属性 | 保留未知属性；仅精确修改目标节点 |
| T13 | 未知 Laya 版本或无法解析的场景 | 退出且零修改 |
| T14 | `apply --dry-run` | 项目文件哈希全不变 |
| T15 | 重复 `build`/`apply` | 幂等，不生成嵌套优化资源 |
| T16 | apply 中途异常 | 恢复原始场景与资源状态 |
| T17 | rollback | 完整恢复修改前文件/资源引用 |
| T18 | 真实 Laya 项目运行 | 新皮肤和九宫格生效；原节点尺寸、位置不变 |
| T19 | Laya 截图对比 | 对关键测试样例提供截图差异及统计 |
| T20 | 原图被外部更新 | 检测 source hash 改变；禁止静默沿用陈旧 manifest |

**引擎集成测试的最低要求**：由 LayaAir IDE 创建一个原生 `Image` 场景作为输入；先在 IDE 中手动设置一份已知有效的 `sizeGrid`，观察并固化该版本真实序列化差异作为 `tests/fixtures/laya/` 基准。不要凭空生成 `.ls/.lh` 属性结构。

---

## 9. 风险与明确边界

1. **LayaAir 项目版本差异**：优先适配用户实际项目版本。若无项目样例，可完整实现算法与 manifest，但不能声称已完成项目回写；需在 README 明确列出未验证部分。
2. **九宫格与整图缩放不同**：节点原始使用尺寸 != PNG 原尺寸时可能改变外观，V1 默认跳过。
3. **GPU 过滤与边缘拼缝**：Python 像素完全一致不自动保证渲染截图一致；必须校验，失败回退。
4. **重复填充 vs 拉伸**：本项目默认 `repeat=0`，不做重复平铺推断。
5. **只优化纹理像素面积**：不承诺减少 DrawCall，不做合图、去重、压缩格式转换。
6. **资源引用可能有 UUID 和元数据**：必须尊重实际 LayaAir 资源系统，否则生成的图虽然存在，场景也可能引用不到。

---

## 10. Codex 实施顺序（请执行，不要只输出设计）

1. 创建 Python 包与 CLI、基本单元测试；生成覆盖场景的合成 RGBA fixture。
2. 实现全等行/列检测、连续区间识别、候选评分、PNG 裁剪。
3. 实现独立 CPU 九宫格还原器与严格逐像素比对；只有验证通过的候选可写入 manifest。
4. 实现 `scan`、`build`、`verify`、报告及哈希幂等机制。
5. 检查真实 LayaAir 项目与版本；用 IDE 生成真实的 `Image + skin + sizeGrid` 场景样本以确定序列化。
6. 实现 `apply --dry-run` 和实际回写，包含新资源导入/引用、字段保存、冲突检测、备份、事务与 rollback。
7. 执行 20 项测试，并以真实 LayaAir 场景验证原图与优化图的渲染效果。
8. 交付 README、CLI 使用样例、兼容性说明、自动化测试结果与一份 `scan/build/apply` 产出的优化报告。

**Codex 最终交付不能只包含算法脚本：必须在实际 LayaAir 项目文件中产生可见的 `skin + sizeGrid` 更新，并说明采用的场景序列化字段或元数据配置方式。** 若实际项目暂不可用，应明确列出已完成部分与未验证的集成项，不能伪造成功。

## 11. 参考资料

- LayaAir Image 组件属性：https://layaair.com/3.x/doc/IDE/uiEditor/uiComponent/Image/readme.html
- LayaAir 3.4 `Image.sizeGrid` API：https://layaair.layabox.com/3.x/api/3.4/classes/laya_ui_Image.Image.html
- LayaAir 3.4 纹理资源级九宫格说明：https://layaair.com/3.4/doc/IDE/assets/texture/readme.html

文档所述 `sizeGrid` 顺序是 LayaAir 官方定义：**top,right,bottom,left,repeat**。场景文件具体序列化格式，以实际用户项目的目标版本验证结果为准。
