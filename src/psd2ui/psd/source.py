"""Read PSD/PSB documents and cut images exclusively through psd-tools."""
from copy import deepcopy
import hashlib
import math
from pathlib import Path

from psd_tools import PSDImage
from psd_tools.constants import BlendMode, Resource

from .pixels import content_bounds, render_bounds, render
from .text import read_text


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def xywh(box):
    return [box[0], box[1], box[2]-box[0], box[3]-box[1]]


class PSDSource:
    """Small source interface used by the shared UI export orchestrator.

    open/inspect return an immutable-value document snapshot; render accepts
    layer index paths from that snapshot. No operation launches a design app,
    serializes PSD modifications, or uses its merged document preview as a cut.
    """
    def __init__(self, *, page_canvas=None, trim_static_smartobjects=None):
        self.page_canvas = page_canvas
        self.trim_static_smartobjects = trim_static_smartobjects
        self.path = None
        self.psd = None
        self._nodes = {}
        self.render_warnings = []

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.psd = None
        self.path = None
        self._nodes = {}
        self._snapshot = None

    def warn(self, code, path, message):
        item = {'code': code, 'path': path, 'message': str(message)}
        if item not in self._warnings:
            self._warnings.append(item)

    def render_warn(self, code, path, message):
        item = {'code': code, 'path': path, 'message': str(message)}
        if item not in self.render_warnings:
            self.render_warnings.append(item)

    def open(self, path):
        path = Path(path).resolve()
        if path.suffix.lower() not in {'.psd', '.psb'} or not path.is_file():
            raise ValueError(f'需要有效 PSD/PSB 文件：{path}')
        before = digest(path)
        psd = PSDImage.open(path)
        if digest(path) != before:
            raise ValueError('读取 PSD 期间源文件发生变化')
        self.path, self.psd, self._sha = path, psd, before
        self._warnings, self.render_warnings, self._nodes = [], [], {}
        dpi = 72.0
        resolution = psd.image_resources.get_data(Resource.RESOLUTION_INFO)
        if resolution is not None:
            horizontal, vertical = resolution.horizontal / 65536, resolution.vertical / 65536
            if not math.isclose(horizontal, vertical, abs_tol=.001):
                raise ValueError(f'PSD 横纵 DPI 不一致：{horizontal} / {vertical}')
            dpi = float(horizontal)
        children = [self._node(layer, [index], ()) for index, layer in enumerate(psd)]
        pages = [child for child in children if '#' not in child['name']]
        single_page=(len(pages)==1 and pages[0]['kind']=='GroupNode'
                     and {'content','bg'}<={c['name'] for c in pages[0]['children']})
        covered=False
        if single_page:
            bx,by,bw,bh=next(c['box'] for c in pages[0]['children'] if c['name']=='bg')
            covered=bx<=0 and by<=0 and bx+bw>=psd.width and by+bh>=psd.height
        use_canvas=self.page_canvas is True or (self.page_canvas is None and single_page and covered)
        if use_canvas:
            if (len(pages) != 1 or pages[0]['kind'] != 'GroupNode'
                    or not {'content','bg'} <= {c['name'] for c in pages[0]['children']}):
                raise ValueError('--page-canvas 只支持有 content/bg 的单页面根；多页保持各自原生范围')
            pages[0]['sourceBox'] = pages[0].get('sourceBox', list(pages[0]['box']))
            pages[0]['preCanvasBox'] = list(pages[0]['box'])
            pages[0]['box'] = pages[0]['visibleBox'] = [0, 0, *psd.size]
            pages[0]['clipToCanvas'] = True
        tree = {'name': '', 'kind': 'DocumentNode', 'indices': [], 'box': [0, 0, *psd.size],
                'visibleBox': [0, 0, *psd.size], 'visible': True, 'opacity': 1,
                'effects': False, 'enclosures': 0, 'transform': [1,0,0,0,1,0], 'children': children}
        self._snapshot = {'path': str(path), 'session': before, 'dpi': dpi,
                          'tree': tree, 'sourceWarnings': deepcopy(self._warnings),
                          'sourceGeometryOptions':dict(pageCanvas=use_canvas,
                               pageCanvasPolicy='auto_background_coverage' if self.page_canvas is None else 'explicit',
                               trimStaticSmartobjects='auto_abnormal_padding' if self.trim_static_smartobjects is None else self.trim_static_smartobjects),
                          'sourceFormat': 'psb' if psd.version == 2 else 'psd'}
        return deepcopy(self._snapshot)

    def _node(self, layer, indices, ancestry):
        path = '/'.join((*ancestry, layer.name))
        group = layer.is_group()
        active_effects = bool(layer.effects.enabled and any(effect.enabled for effect in layer.effects))
        trim = False if any(name.partition('_')[0]=='icon' for name in (*ancestry,layer.name)) else self.trim_static_smartobjects
        bounds = content_bounds(layer, trim_static_smartobjects=trim)
        viewport = render_bounds(layer, trim_static_smartobjects=trim)
        if layer.name.partition('_')[0] == 'icon':
            # PSD pixel-layer canvases retain transparent padding; including
            # hidden descendants also allows an explicit icon-canvas group.
            viewport = bounds
        if viewport[2] <= viewport[0] or viewport[3] <= viewport[1]:
            viewport = bounds
        result = {'name': layer.name, 'kind': 'GroupNode' if group else 'ShapeNode',
                  'indices': indices, 'box': xywh(bounds), 'visibleBox': xywh(viewport),
                  'visible': bool(layer.visible), 'opacity': layer.opacity / 255,
                  'effects': active_effects,
                  'enclosures': int(layer.has_mask()) + int(layer.has_vector_mask()),
                  'transform': [1,0,0,0,1,0], 'children': []}
        self._nodes[tuple(indices)] = (layer, result, path)
        if tuple(bounds) != tuple(layer.bbox):
            result['sourceBox'] = xywh(layer.bbox)
        if '#' in layer.name:
            # Ignored design subtrees are never rendered or interpreted, so an
            # unsupported text/effect inside them cannot invalidate a page.
            return result
        if layer.blend_mode not in (BlendMode.NORMAL, BlendMode.PASS_THROUGH):
            self.warn('PSD_BLEND_MODE', path, f'混合模式 {layer.blend_mode.name} 可能依赖其它图层背景')
        if layer.clipping or layer.has_clip_layers():
            self.warn('PSD_CLIPPING', path, '剪贴蒙版依赖相邻图层，切图需人工复核')
        if active_effects:
            self.warn('PSD_LAYER_EFFECT', path, '图层效果由 psd-tools 近似渲染；可编辑文字/容器效果不完全映射')
        if layer.kind not in ('group', 'pixel', 'type'):
            self.warn('PSD_CACHED_LAYER', path, f'{layer.kind} 依赖 PSD 缓存像素或 psd-tools 有限渲染，不调用外部设计软件')
        if group:
            if layer.opacity != 255:
                self.warn('PSD_GROUP_OPACITY', path,
                          'PSD 组透明度映射为运行时容器 alpha；重叠内容的合成需人工复核')
            result['children'] = [self._node(child, [*indices, index], (*ancestry, layer.name))
                                  for index, child in enumerate(layer)]
        elif layer.kind == 'type':
            data, text_box = read_text(layer, path, self.warn)
            result.update(data, kind='TextNode', box=xywh(text_box))
        return result

    def _check(self, request):
        if self.path is None:
            raise ValueError('请先打开 PSD 文档')
        if request.get('path') and Path(request['path']).resolve() != self.path:
            raise ValueError('请求 PSD 路径与当前文档不一致')
        if request.get('session') and request['session'] != self._sha:
            raise ValueError('PSD 文档会话已变化')
        if digest(self.path) != self._sha:
            raise ValueError('PSD 源文件发生变化，停止导出')

    def script(self, request):
        self._check(request)
        action = request.get('action')
        if action == 'inspect':
            return deepcopy(self._snapshot)
        if action != 'render':
            raise ValueError(f'未知 PSD 操作：{action}')
        result = []
        for job in request['jobs']:
            layer, node, path = self._nodes[tuple(job['indices'])]
            if job['name'] != layer.name:
                raise ValueError(f'PSD 图层与采集记录不一致：{job["name"]}')
            x, y, width, height = node['visibleBox']
            box = (math.floor(x), math.floor(y), math.ceil(x+width), math.ceil(y+height))
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError(f'图片没有有效像素画布：{path}')
            output = Path(job['output'])
            output.parent.mkdir(parents=True, exist_ok=True)
            image = render(layer, box, self.render_warn, path)
            try:
                image.save(output, format='PNG')
            finally:
                image.close()
            result.append({'output': str(output), 'box': xywh(box)})
        self._check(request)
        return result
