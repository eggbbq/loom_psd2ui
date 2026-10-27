"""Read editable PSD text without converting it into a bitmap."""
import math

from psd2ui.text import text_bounds


class Diagnostics:
    def __init__(self, warn):
        self.warn = warn


def fill(values):
    alpha, red, green, blue = map(float, values)
    channels = [max(0, min(255, round(channel * 255))) for channel in (red, green, blue)]
    return {'color': '#' + ''.join(f'{channel:02x}' for channel in channels),
            'alpha': max(0, min(1, alpha))}


def read_text(layer, path, warn):
    try:
        typesetting = layer.typesetting
        runs = [run for run in typesetting.runs if run.text.strip('\r\n\x00')]
        if not runs:
            raise ValueError('没有可读取的文字样式 run')
        style = runs[0].style
        if style._get('FontSize') is None or not style.font_name or style.fill_color is None:
            raise ValueError('缺少字体、字号或填充颜色')
        transform = tuple(map(float, layer.transform))
        if len(transform) != 6 or not all(math.isfinite(value) for value in transform):
            raise ValueError('文字变换无效')
        a, b, c, d, tx, ty = transform
        if not math.isfinite(style.font_size) or style.font_size <= 0 or abs(a*d-b*c) < 1e-12:
            raise ValueError('文字字号或变换矩阵无效')
        paragraph = int(typesetting.paragraphs[0].style.justification) if typesetting.paragraphs else 0
        alignment = {0: 'left', 1: 'right', 2: 'center'}.get(paragraph, 'left')
        result = {'text': layer.text.replace('\r\n', '\n').replace('\r', '\n').rstrip('\x00'),
                  'font': style.font_name, 'fontSize': float(style.font_size),
                  'fill': fill(style.fill_color), 'align': alignment,
                  'paragraphAlign': {'left': 0, 'center': 1, 'right': 2}[alignment],
                  'transform': [a, b, tx, c, d, ty], 'runs': []}
        offset = 0
        for run in runs:
            end = offset + len(run.text)
            result['runs'].append({'begin': offset, 'end': end,
                                   'font': run.style.font_name,
                                   'fontSize': float(run.style.font_size),
                                   'fill': fill(run.style.fill_color)})
            offset = end
        justifications = {int(paragraph.style.justification) for paragraph in typesetting.paragraphs}
        if len(justifications) > 1:
            warn('MIXED_PARAGRAPH_STYLE', path, '多个段落对齐方式，暂使用首段设置')
        if paragraph not in (0, 1, 2):
            warn('TEXT_ALIGNMENT', path, '特殊段落对齐暂按左对齐导出')
        if (style.faux_bold or style.faux_italic or style.stroke_flag
                or style._get('Tracking', 0) or style._get('BaselineShift', 0)
                or int(typesetting.writing_direction or 0) != 0):
            warn('TEXT_DECORATION', path, '模拟粗斜体、描边、字距、基线或竖排文字样式未完全映射')
        box = text_bounds(layer, Diagnostics(warn), path)
        return result, box
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f'无法读取可编辑文本样式：{path}: {error}') from error
