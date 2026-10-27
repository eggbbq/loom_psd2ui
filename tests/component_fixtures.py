"""Real PSD fixtures written with psd-tools only; no graphics applications."""
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw
from psd_tools import PSDImage
from psd_tools.api.layers import Group, PixelLayer, TypeLayer


def rectangle(parent, name, box, color, border=None):
    x, y, width, height = box
    image = Image.new('RGBA', (width, height), color)
    if border:
        ImageDraw.Draw(image).rectangle((0, 0, width-1, height-1), outline=border, width=2)
    return PixelLayer.frompil(image, parent, name=name, top=y, left=x)


def fixture_page(psd, name='FixturePanel', x=0, selected=False, color='#332050'):
    root = Group.new(psd, name)
    bg = Group.new(root, 'bg')
    rectangle(bg, 'paint', (x, 0, 256, 384), color)
    content = Group.new(root, 'content')
    button = Group.new(content, 'btn_login')
    rectangle(button, 'bg', (x+24, 24, 80, 32), '#5544aa', '#110022')
    control = Group.new(content, 'switch_sound')
    rectangle(control, 'bg', (x+128, 24, 80, 32), '#442244', '#110022')
    off = Group.new(control, 'off')
    rectangle(off, 'image_off', (x+144, 32, 48, 16), '#dd3333')
    on = Group.new(control, 'on')
    rectangle(on, 'image_on', (x+144, 32, 48, 16), '#33dd33')
    off.visible = not selected
    on.visible = selected
    listing = Group.new(content, 'list_tasks')
    rectangle(listing, 'bg', (x+24, 88, 184, 144), '#113355')
    cells = Group.new(listing, 'content')
    for index in range(3):
        cell = Group.new(cells, f'item_{index+1}')
        rectangle(cell, 'bg', (x+32, 100+index*36, 168, 28), '#888888', '#222222')
        rectangle(cell, 'img_status', (x+36, 104+index*36, 12, 12), '#00dd88')
    icon = Group.new(content, 'icon_coin')
    icon_image = Image.new('RGBA', (32, 32), '#00000000')
    ImageDraw.Draw(icon_image).rectangle((8, 8, 23, 23), fill='#ffff00')
    PixelLayer.frompil(icon_image, icon, 'paint', left=x+24, top=264)
    ignored = Group.new(content, '#draft')
    rectangle(ignored, 'paint', (x-20, -20, 512, 512), '#ff00ff')
    return root


def make_psd(path, *, pages=('FixturePanel',), selected=False, version=1):
    """Write a genuine layered PSD/PSB with current project's fixed names."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    psd = PSDImage.new('RGBA', (256*len(pages), 384))
    psd._record.header.version = version
    for index, name in enumerate(pages):
        fixture_page(psd, name, x=index*256, selected=selected)
    psd.save(path)
    return path


def first_text_layer(document):
    for layer in document.descendants():
        if layer.kind == 'type':
            return layer
    raise ValueError('The provided PSD has no real type layer')


def clone_type_layer(source, parent, name, left, top, *, visible=True):
    """Create a temporary real type-layer fixture from user-provided PSD records."""
    record, channels = deepcopy(source._record), deepcopy(source._channels)
    layer = TypeLayer(parent, record, channels)
    parent.append(layer)
    dx, dy = left-layer.left, top-layer.top
    layer.left = left
    layer.top = top
    matrix = list(layer._data.transform)
    matrix[4] += dx
    matrix[5] += dy
    layer._data.transform = tuple(matrix)
    layer.name = name
    layer.visible = visible
    return layer


def make_text_psd(path, provided_source):
    """Exercise real text parsing without ever modifying the user's original PSD."""
    provided = PSDImage.open(provided_source)
    sample = first_text_layer(provided)
    psd = PSDImage.new('RGBA', (256, 384))
    root = Group.new(psd, 'TextPanel')
    rectangle(root, 'bg', (0, 0, 256, 384), '#223344')
    content = Group.new(root, 'content')
    input_group = Group.new(content, 'input_password')
    rectangle(input_group, 'bg', (24, 24, 208, 60), '#333333')
    clone_type_layer(sample, input_group, 'title', 40, 40, visible=False)
    clone_type_layer(sample, input_group, 'placeholder', 40, 40)
    button = Group.new(content, 'btn_login')
    rectangle(button, 'bg', (24, 120, 208, 60), '#334477')
    clone_type_layer(sample, button, 'title', 40, 136)
    psd.save(path)
    return Path(path), sample.text
