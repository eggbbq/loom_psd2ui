"""Reproducible real layered PSD fixture; no Photoshop or third-party artwork."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
from psd_tools.api.layers import Group, PixelLayer, TypeLayer
from psd_tools.constants import BlendMode, Tag
from psd_tools.psd import engine_data as ed
from psd_tools.psd.descriptor import Descriptor, DescriptorBlock, Double, RawData, String
from psd_tools.psd.tagged_blocks import TaggedBlock, TypeToolObjectSetting


def pixel(parent, name, color, xy=(0, 0), size=(16, 16), visible=True, opacity=255):
    layer = PixelLayer.frompil(Image.new("RGBA", size, color), parent=parent, name=name,
                                      left=xy[0], top=xy[1], opacity=opacity)
    layer.visible, layer.opacity = visible, opacity
    return layer


def group(parent, name, visible=True, opacity=255):
    layer = Group.new(parent, name=name)
    # Set the Unicode name through the API, which also supplies a valid legacy
    # Pascal-string fallback for non-MacRoman names.
    layer.name = name
    layer.blend_mode = BlendMode.NORMAL
    layer.visible, layer.opacity = visible, opacity
    return layer


def engine(value):
    if isinstance(value, dict):
        result = ed.Dict()
        for key, child in value.items():
            result[key] = engine(child)
        return result
    if isinstance(value, list):
        return ed.List([engine(child) for child in value])
    if isinstance(value, str):
        return ed.String(value)
    if isinstance(value, bool):
        return ed.Bool(value)
    return ed.Integer(value) if isinstance(value, int) else ed.Float(value)


def text(parent, name="Title", value="Shop\rUI", xy=(20, 25), readable=True, rich=False):
    image = Image.new("RGBA", (90, 32))
    ImageDraw.Draw(image).text((0, 0), value.replace("\r", "\n"), fill="white", font=ImageFont.load_default(size=12))
    cached = PixelLayer.frompil(image, parent=parent, name=name, left=xy[0], top=xy[1])
    style = {"Font": 0, "FontSize": 12.0, "FillColor": {"Type": 1, "Values": [1.0, 1.0, 1.0, 1.0]}}
    if not readable:
        style.pop("FillColor")
    styles = [style]
    lengths = [len(value)]
    if rich:
        styles.append({**style, "FontSize": 18.0})
        lengths = [1, len(value) - 1]
    data = engine({"EngineDict": {
        "Editor": {"Text": value},
        "StyleRun": {"RunArray": [{"StyleSheet": {"StyleSheetData": s}} for s in styles], "RunLengthArray": lengths},
        "ParagraphRun": {"RunArray": [{"ParagraphSheet": {"Properties": {"Justification": 0}}}], "RunLengthArray": [len(value)]},
    }, "ResourceDict": {"FontSet": [{"Name": "Arial"}]}})
    settings = TypeToolObjectSetting(text_version=50, transform=(1.0, 0.0, 0.0, 1.0, *map(float, xy)),
                                     text_data=DescriptorBlock(items={b"Txt ": String(value), b"EngineData": RawData(data),
                                         b"bounds": Descriptor(items={b"Left": Double(0), b"Top ": Double(0),
                                                                      b"Rght": Double(90), b"Btom": Double(32)})}))
    cached.tagged_blocks[Tag.TYPE_TOOL_OBJECT_SETTING] = TaggedBlock(key=Tag.TYPE_TOOL_OBJECT_SETTING, data=settings)
    layer = TypeLayer(parent, cached._record, cached._channels)
    layer.name = name
    index = parent.index(cached)
    parent.remove(cached)
    parent.insert(index, layer)
    return layer


def make_fixture(path):
    psd = PSDImage.new("RGBA", (320, 240))
    settings = group(psd, "Settings", visible=False)
    pixel(settings, "Background", "#102030", (5, 10), (280, 200))
    text(settings, "Settings title", "Settings", (20, 25))
    shop = group(psd, "Shop")
    pixel(shop, "Background", "#293343", (10, 20), (280, 200))
    nested = group(shop, "Nested")
    pixel(nested, "Red", "red", (30, 50), (60, 60))
    pixel(nested, "Green", "lime", (50, 70), (60, 60))
    pixel(nested, "img_Blue", "blue", (70, 90), (60, 60))
    pixel(nested, "Hidden", "white", (-10, -20), (10, 10), visible=False)
    text(shop)
    hidden = group(shop, "Hidden group", visible=False)
    pixel(hidden, "Locally visible", "cyan", (300, 225), (5, 5))
    pixel(hidden, "Locally hidden", "magenta", (290, 220), (5, 5), visible=False)
    bake = group(shop, "img_Baked", visible=False, opacity=128)
    pixel(bake, "Included", "yellow", (210, 40))
    pixel(bake, "#Excluded", "red", (210, 40))
    ignored = group(bake, "Ignore# subtree")
    pixel(ignored, "Must not appear", "magenta", (200, 30), (30, 30))
    pixel(bake, "Hidden child", "blue", (210, 40), visible=False)
    text(shop, "img_Raster text", "Baked text", (200, 130))
    pixel(shop, "#Reference", "red")
    excluded = group(shop, "img_Panel#")
    pixel(excluded, "Ignore descendant", "red")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    psd.save(path)
    return path


def make_tag_fixture(path, extended=False):
    """Real PSD for native container tag/automatic layout verification."""
    psd = PSDImage.new("RGBA", (320, 240))
    for prefix, name, xy in (("hbox_", "Row", (10, 10)),
                             ("vhox_", "Column", (10, 90)),
                             ("panel_", "Window", (180, 90))):
        parent = group(psd, prefix + name)
        text(parent, "First", "A", xy)
        offset = (105, 0) if name == "Row" else (0, 44) if name == "Column" else (15, 10)
        text(parent, "Second", "B", (xy[0] + offset[0], xy[1] + offset[1]))
    if extended:
        for prefix, name in (("pnl_", "ShortPanel"), ("button_", "Button"),
                             ("btn_", "ShortButton"), ("list_", "List"),
                             ("progressbar_", "Progress"), ("bar_", "ShortProgress"), ("combobox_", "Combo"),
                             ("gslider_", "Slider"), ("loader_", "Loader"),
                             ("icon_", "Icon"), ("ico_", "ShortIcon"), ("label_", "Generic"),
                             ("背景_", "ChineseBackground"), ("按钮_", "ChineseButton"),
                             ("边框_", "ChineseBorder"), ("图标_", "ChineseIcon"),
                             ("图片_", "ChineseImage"), ("花边_", "ChineseTrim"), ("底板_", "ChineseBase"),
                             ("GButton_", "Exact"), ("img_", "NativeImage")):
            parent = group(psd, prefix + name)
            text(parent, "First", "A", (10, 10))
            text(parent, "Second", "B", (25, 20))
        pixel(psd, "btn_Leaf", "red", (10, 10))
        text(psd, "txt_Caption", "UI", (10, 10))
        text(psd, "title_Heading", "Heading", (10, 10))
        text(psd, "标题_ChineseTitle", "Heading", (10, 10))
        text(psd, "input_Account", "Account", (10, 10))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    psd.save(path)
    return path


if __name__ == "__main__":
    print(make_fixture(Path(__file__).parent / "fixtures/rules.psd"))

