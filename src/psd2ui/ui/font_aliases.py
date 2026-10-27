"""Automatic native font fallback and optional aliases; source records stay intact."""
import json
from pathlib import Path
import re
import sys


def available_families():
    """Read native font families; never open an app or download font assets."""
    if sys.platform!='darwin':return []
    import ctypes
    core=ctypes.CDLL('/System/Library/Frameworks/CoreText.framework/CoreText')
    cf=ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    core.CTFontManagerCopyAvailableFontFamilyNames.restype=ctypes.c_void_p
    cf.CFArrayGetCount.argtypes=[ctypes.c_void_p];cf.CFArrayGetCount.restype=ctypes.c_long
    cf.CFArrayGetValueAtIndex.argtypes=[ctypes.c_void_p,ctypes.c_long];cf.CFArrayGetValueAtIndex.restype=ctypes.c_void_p
    cf.CFStringGetCString.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_long,ctypes.c_uint32];cf.CFStringGetCString.restype=ctypes.c_bool
    cf.CFRelease.argtypes=[ctypes.c_void_p]
    values=core.CTFontManagerCopyAvailableFontFamilyNames();result=[]
    try:
        for index in range(cf.CFArrayGetCount(values)):
            buf=ctypes.create_string_buffer(1024)
            if cf.CFStringGetCString(cf.CFArrayGetValueAtIndex(values,index),buf,len(buf),0x08000100):result.append(buf.value.decode('utf-8'))
    finally:cf.CFRelease(values)
    return result


def automatic_font_aliases(snapshot,families=None):
    text=[]
    def visit(node):
        if 'text' in node:text.append(node)
        for child in node.get('children',[]):visit(child)
    visit(snapshot['tree'])
    if not text:return {}
    families=available_families() if families is None else families
    normalized=lambda value:re.sub(r'[^\w]','',value).casefold()
    lookup={normalized(family):family for family in families}
    result={}
    for source in sorted({node['font'] for node in text}):
        source_nodes=[node for node in text if node['font']==source]
        base=source.split('-')[0]
        base=re.sub(r'MT$','',base)
        target=lookup.get(normalized(source)) or lookup.get(normalized(base))
        bold=bool(re.search(r'bold|black|heavy|semibold',source,re.I))
        if target is None:
            cjk=any(ord(char)>=0x2e80 for node in source_nodes for char in node['text'])
            choices=('PingFang SC','Heiti SC','Noto Sans CJK SC','Arial Unicode MS') if cjk else ('Arial','Helvetica','DejaVu Sans')
            target=next((family for family in choices if normalized(family) in lookup),'sans-serif')
        if target!=source or bold:result[source]=dict(family=target,bold=bold)
    return result


def validate_font_aliases(config):
    if config is None:
        return {}
    if not isinstance(config,dict):
        raise ValueError('字体映射必须是源字体名称到 family/bold 的对象')
    result={}
    for source,style in config.items():
        if not isinstance(source,str) or not source or not isinstance(style,dict) or set(style)-{'family','bold'}:
            raise ValueError(f'无效字体映射：{source!r}')
        family=style.get('family')
        if not isinstance(family,str) or not family.strip() or any(ord(c)<32 for c in family):
            raise ValueError(f'字体映射需要有效 family：{source}')
        if 'bold' in style and type(style['bold']) is not bool:
            raise ValueError(f'字体映射 bold 必须为布尔值：{source}')
        result[source]=dict(style)
    return result


def load_font_aliases(path):
    return validate_font_aliases(json.loads(Path(path).read_text(encoding='utf-8')))


def apply_font_aliases(layout,config):
    changes=[]
    def visit(node,ancestors=()):
        path='/'.join((*ancestors,node['name']))
        if node.get('type')=='text' and node.get('font') in config:
            source=node['font'];alias=config[source]
            node['fontAliasSource']=source
            node['font']=alias['family']
            if 'bold' in alias:node['bold']=alias['bold']
            changes.append(dict(path=path,sourceFont=source,**alias))
        for child in node.get('children',[]):visit(child,(*ancestors,node['name']))
    visit(layout)
    return changes
