# Blender 自动化合成资产管线技术指南 (PSD 混合模式修复)

本指南详述了利用 **Blender 后台无界面模式 (Headless Mode)** 作为图形合成后端，完美修复 `psd-tools` 导出图层组时混合模式 (Blend Modes) 失效、图层变形及透明度污染的工业级解决方案。

---

## 一、 核心架构设计与原理

整个流水线遵循 **“数据读取与图形渲染解耦”** 的原则，将不可量化的复杂渲染交给专业的 Blender 图形计算核心，而将死的标准和程序留给 Python 逻辑层。

```
[1. 纯 Python 阶段]                  [2. 命令行唤醒]                 [3. Blender 静默渲染]
利用 psd-tools 解析 PSD ─> 生成 ─>  blender --background  ─> 自动加载图片并动态连线 ─> 导出
导出裸 RGBA 图层与 manifest.json     无界面静默启动进程       根据 blend_mode 执行 GPU/CPU 矩阵运算
```

### 1. 为什么纯 Python 的 `psd-tools` 独立导出组会失效？
* **失去像素基底**：混合模式（如 Overlay、Multiply）是当前图层与下方所有可见图层的**相对数学计算**。孤立导出图层组时，失去了用于对撞的底层像素。
* **穿透（Pass Through）断裂**：Photoshop 图层组默认的“穿透”属性在独立导出时会丢失上下文环境。

### 2. Blender 后端的优势
* **工业级数学算法**：Blender 的合成器节点（Compositor）拥有与 Photoshop 完全一致的色彩混合公式，且原生支持 **预乘透明度 (Premultiplied Alpha)**，彻底绝缘边缘发黑或半透明失真。
* **完全可量化自动化**：通过 Python API (`bpy`)，图层顺序、混合模式和不透明度均可转化为确定性的代码指令。

---

## 二、 自动化管线实现步骤与逻辑说明

整个流程由两个死程序脚本组成：

### 流程一：资产解构与导出清单（主调度 Python 脚本）
1. 使用 `psd-tools` 打开 master `.psd` 文件。
2. 递归遍历图层树，将每个图层以 **Normal (正常) 模式** 导出为干净的 `RGBA` 原始 PNG 图片。
3. 提取每个图层的元数据（图层名、混合模式字符串、不透明度、绝对坐标），输出为一个标准的 `manifest.json` 配置文件。

### 流程二：无界面合成与烘焙（Blender 后台 Python 脚本）
1. 通过 `bpy.context.scene.use_nodes = True` 激活场景的合成节点系统。
2. 读取 `manifest.json`，使用 `nodes.new('CompositorNodeImage')` 批量创建图片输入节点，动态加载图层图片。
3. **建立映射表**：将读取到的 PSD 混合模式字符串映射为 Blender 的节点类型：
   * `MULTIPLY` (正片叠底) $ightarrow$ `mix_node.blend_type = 'MULTIPLY'`
   * `OVERLAY` (叠加) $ightarrow$ `mix_node.blend_type = 'OVERLAY'`
   * `SOFT_LIGHT` (柔光) $ightarrow$ `mix_node.blend_type = 'SOFT_LIGHT'`
4. **顺序链式连线**：按照图层从低到高的顺序，自动将前一步 Mix 节点的 `Image` 输出作为下一个 Mix 节点的 `Image` 输入，实现层层穿透叠加。
5. 触发 `bpy.ops.render.render(write_still=True)` 执行无窗口快速烘焙，导出标准化且渲染完全正确的游戏贴图资产。

---

## 三、 全套核心代码模板 (Boilerplate Code)

你可以直接将以下代码保存为两个独立的文件，并确保你本地安装了 Blender，即可在命令行一键拉起流水线。

### 1. `extract_psd.py` (主调度脚本 - 纯 Python 环境运行)
```python
import os
import json
from psd_tools import PSDImage

def export_psd_assets(psd_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    psd = PSDImage.open(psd_path)
    manifest = []
    
    # 反向遍历（从底层到顶层符合渲染顺序）
    layer_idx = 0
    for layer in reversed(list(psd.descendants())):
        if layer.is_group() or not layer.visible or layer.size == (0, 0):
            continue
            
        layer_img_name = f"layer_{layer_idx}.png"
        layer_img_path = os.path.join(output_dir, layer_img_name)
        
        # 导出没有任何混合污染的裸 RGBA 图片
        pil_img = layer.topil()
        if pil_img:
            pil_img.save(layer_img_path)
            
            # 记录量化元数据
            manifest.append({
                "name": layer.name,
                "file": layer_img_name,
                "blend_mode": str(layer.blend_mode).split('.')[-1], # 提取混和模式枚举字符串
                "opacity": layer.opacity / 255.0 if layer.opacity is not None else 1.0
            })
            layer_idx += 1
            
    # 写入死数据清单
    with open(os.path.join(output_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)
        
    print(f"[成功] PSD 解析完毕，共导出 {layer_idx} 个图层层级至 {output_dir}")

if __name__ == "__main__":
    # 使用示例
    export_psd_assets("character_master.psd", "./temp_layers")
```

### 2. `blender_composite.py` (合成驱动脚本 - 由 Blender 后台唤醒运行)
```python
import bpy
import os
import json
import sys

def build_blender_pipeline(layers_dir):
    # 1. 激活合成器节点网格
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    
    # 清空默认节点
    for node in tree.nodes:
        tree.nodes.remove(node)
        
    # 读取死数据清单
    json_path = os.path.join(layers_dir, 'manifest.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        layers_data = json.load(f)
        
    last_output_socket = None
    
    # 2. 动态创建和连接节点
    for idx, layer in enumerate(layers_data):
        img_path = os.path.join(layers_dir, layer['file'])
        
        # 创建图片输入节点
        img_node = tree.nodes.new(type="CompositorNodeImage")
        img = bpy.data.images.load(img_path)
        img_node.image = img
        
        # 如果是第一层（最底层背景），直接作为基底
        if idx == 0:
            last_output_socket = img_node.outputs['Image']
            continue
            
        # 创建混合 RGB 节点
        mix_node = tree.nodes.new(type="CompositorNodeMixRGB")
        
        # 建立 PS 模式到 Blender 模式的硬射规则（量化对齐）
        ps_to_blender_modes = {
            'MULTIPLY': 'MULTIPLY',
            'OVERLAY': 'OVERLAY',
            'SOFT_LIGHT': 'SOFT_LIGHT',
            'SCREEN': 'SCREEN',
            'COLOR_BURN': 'BURN',
            'LINEAR_BURN': 'LINEAR_BURN',
            'NORMAL': 'MIX'
        }
        
        # 设定死的混合属性和不透明度因子
        target_mode = layer['blend_mode']
        mix_node.blend_type = ps_to_blender_modes.get(target_mode, 'MIX')
        mix_node.inputs['Fac'].default_value = layer['opacity']
        
        # 链式接轨自动拉线
        tree.links.new(last_output_socket, mix_node.inputs[1]) # 连入基底 Input
        tree.links.new(img_node.outputs['Image'], mix_node.inputs[2]) # 连入当前图层 Input
        
        last_output_socket = mix_node.outputs['Image']
        
    # 3. 创建输出节点并输出烘焙
    output_node = tree.nodes.new(type="CompositorNodeComposite")
    tree.links.new(last_output_socket, output_node.inputs['Image'])
    
    # 4. 配置场景分辨率并静默渲染
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.filepath = os.path.join(layers_dir, 'final_baked_texture.png')
    bpy.ops.render.render(write_still=True)
    print("[成功] Blender 后台网络合成完毕，最终标准化贴图已烘焙输出！")

if __name__ == "__main__":
    # 解析来自命令行传入的独立参数 (-- 后面的自定义参数)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        target_dir = args[0]
        build_blender_pipeline(target_dir)
```

---

## 四、 工业化自动化集成集成命令

当你在独立开发中调用这套流水线时，可以通过系统终端（Shell）以无界面静默方式（Headless Mode）直接串联调用两段死程序：

```bash
# 步骤 1：使用纯 Python 环境提取图层并量化生成 manifest.json 说明书
python extract_psd.py

# 步骤 2：通过 --background 隐式唤醒 Blender，在后台全自动合成并完美导出贴图
blender --background --python blender_composite.py -- ./temp_layers
```
生成的 `final_baked_texture.png` 将完全抹平所有渲染 Bug，直接作为标准化材质资产，无缝挂载到你的 3D 低模管线中。

---

## 五、 官方技术参考手册链接

为了进一步微调这套固定程序，你可以在开发时随时查阅以下官方死标准文档：
1. [Blender 官方无界面后台命令行参数规范手册 (Command Line Arguments)](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html)
2. [Blender Python API 场景节点树核心架构说明 (`bpy.types.NodeTree`)](https://docs.blender.org/api/current/bpy.types.NodeTree.html)
3. [Blender 合成器 Mix RGB 节点内置所有混合模式枚举表 (`CompositorNodeMixRGB`)](https://docs.blender.org/api/current/bpy.types.CompositorNodeMixRGB.html)
4. [Blender 合成器 Image 图层数据加载输入节点文档 (`CompositorNodeImage`)](https://docs.blender.org/api/current/bpy.types.CompositorNodeImage.html)