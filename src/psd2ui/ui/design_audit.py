"""Read-only diagnostics for the existing component naming convention."""
import re

from .layout import LayoutBuilder, token


class DesignValidationError(ValueError):
    def __init__(self, report):
        self.diagnostics = report
        super().__init__('PSD 不符合组件规范：' + '; '.join(item['message'] for item in report['errors'][:6]))


def inspect_design(snapshot):
    errors, roots = [], []
    def error(code,path,message):errors.append(dict(code=code,path=path,message=message))
    def candidates(node):
        if '#' in node['name']:return
        if node['kind'] in ('DocumentNode','SpreadNode','ArtboardNode','LayerNode'):
            for child in node['children']:candidates(child)
        else:roots.append(node)
    candidates(snapshot['tree'])
    if not roots:error('NO_PAGES','/','没有可导出的页面根组')
    if abs(snapshot['dpi']-72)>.001:error('DOCUMENT_DPI','/','设计稿要求 72DPI，实际为 '+str(snapshot['dpi']))
    seen=set()
    def structure(node,path):
        if '#' in node['name']:return
        children=[c for c in node['children'] if '#' not in c['name']]
        names=[c['name'] for c in children]
        if len({n.casefold() for n in names}) != len(names):error('DUPLICATE_INTERFACE',path,'同一父节点存在重名接口：'+path)
        kind=token(node['name'])
        if kind=='icon':
            x,y,w,h=node['box']
            if w!=h or w<16 or w!=int(w) or int(w)&(int(w)-1):error('ICON_CANVAS',path,'icon 需要至少16px、2的幂次正方形画布：'+path)
        if kind in {'switch','tab'}:
            states={c['name']:c['visible'] for c in children}
            if not {'on','off'}<=states.keys() or states.get('on')==states.get('off'):
                error('EXCLUSIVE_STATES',path,'需要初始互斥的 on/off 分组：'+path)
        if kind=='input':
            title=next((c for c in children if c['name']=='title'),None)
            if title is None or 'text' not in title:error('INPUT_TITLE',path,'input 需要可编辑 title 文本：'+path)
        for child in children:structure(child,path+'/'+child['name'])
    for root in roots:
        path=root['name'];valid=True
        if root['kind']!='GroupNode' or not re.fullmatch(r'[A-Z][A-Za-z0-9]*',path):
            error('PAGE_ROOT_NAME',path,'页面根必须为独立 PascalCase 组：'+path);valid=False
        if path.casefold() in seen:error('DUPLICATE_PAGE',path,'页面根名重复：'+path);valid=False
        seen.add(path.casefold())
        missing={'content','bg'}-{c['name'] for c in root['children']}
        if missing:error('PAGE_INTERFACES',path,'页面根缺少直属 '+ '/'.join(sorted(missing))+'：'+path);valid=False
        structure(root,path)
        if valid:
            try:LayoutBuilder().build(root)
            except (ValueError,KeyError,TypeError) as exc:error('COMPONENT_MAPPING',path,str(exc))
    return dict(valid=not errors,source=snapshot.get('path'),errors=errors,warnings=snapshot.get('sourceWarnings',[]))


def check_source(source, output=None, *, root=None):
    """Read-only source check, with an external JSON report; never repairs PSD."""
    from pathlib import Path
    import json
    from ..psd import PSDSource
    from .exporter import sha256
    from .environment import workspace_root
    root=Path(root or workspace_root()).resolve();source=(root/Path(source)).resolve()
    before=sha256(source)
    with PSDSource() as adapter:snapshot=adapter.open(source)
    report=inspect_design(snapshot)
    if sha256(source)!=before:raise ValueError('检查期间源文件已变化')
    report.update(sourceSha256=before,dpi=snapshot['dpi'],sourceUnchanged=True)
    output=(root/Path(output)).resolve() if output else root/'out/design-check'/(source.stem+'.json')
    if output==source or output.suffix.lower() in {'.psd','.psb'}:raise ValueError('报告不能覆盖源 PSD/PSB')
    if any(any(parent.glob('*.laya')) for parent in output.parents):raise ValueError('诊断报告必须位于 Laya 工程外')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report,output
