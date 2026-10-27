import os
"""Explicit geometry options must fix cache padding without changing PSDs."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
from psd_tools import PSDImage

from tests.component_fixtures import make_psd, rectangle
from psd2ui.psd.pixels import cached_bounds, content_bounds, render_bounds
from psd2ui.psd.source import PSDSource
from psd2ui.ui.exporter import make_plans, export_feature

ROOT = Path(__file__).resolve().parents[1]
PAGE_FIXTURE = Path(os.environ.get('PSD2UI_COMPONENT_PSD_FIXTURE',ROOT/'tests/fixtures/component_page.psd'))


class Cache:
    kind = 'smartobject'
    name = 'img_static'
    visible = True
    effects = []
    bbox = (-100, -50, 300, 250)
    def __init__(self, empty=False):
        self.image = Image.new('RGBA', (400, 300))
        if not empty:
            ImageDraw.Draw(self.image).rectangle((140,100,159,119), fill='#ff00ffff')
    def topil(self):return self.image
    def is_group(self):return False


class Folder:
    kind='group'
    visible=True
    effects=[]
    bbox=Cache.bbox
    def __init__(self,name,child):self.name,self.child=name,child
    def __iter__(self):return iter([self.child])
    def is_group(self):return True


class PSDGeometryTests(unittest.TestCase):
    def test_static_cache_trim_is_opt_in_and_keeps_empty_canvas(self):
        cache = Cache()
        self.assertEqual(cached_bounds(cache), cache.bbox)
        self.assertEqual(cached_bounds(cache,trim_static_smartobjects=True), (40,50,60,70))
        self.assertEqual(cached_bounds(Cache(empty=True),trim_static_smartobjects=True), cache.bbox)

    def test_icon_subtree_retains_cache_canvas_even_when_static_trim_is_enabled(self):
        cache=Cache()
        for read_bounds in (content_bounds,render_bounds):
            self.assertEqual(read_bounds(Folder('icon',cache),trim_static_smartobjects=True),cache.bbox)
            self.assertEqual(read_bounds(Folder('bg',cache),trim_static_smartobjects=True),(40,50,60,70))

    def test_single_page_document_canvas_clips_page_without_clipping_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);path=make_psd(folder/'Fixture.psd')
            psd=PSDImage.open(path);content=next(x for x in psd[0] if x.name=='content')
            rectangle(content,'img_decoration',(-40,-20,600,440),'#998877')
            rectangle(content,'img_hit_area',(20,20,64,64),'#00000000')
            psd.save(path)
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            with PSDSource(page_canvas=False) as adapter:
                old=make_plans(adapter.open(path))[0][1]
                self.assertEqual(old['size'],[600,440])
            with PSDSource(page_canvas=True,trim_static_smartobjects=True) as adapter:
                snapshot=adapter.open(path);builder,layout=make_plans(snapshot)[0]
                self.assertEqual(layout['size'],[256,384])
                self.assertEqual(layout['position'],[0,0])
                self.assertTrue(layout['clipToCanvas'])
                nodes={}
                def walk(node):
                    nodes[node['name']]=node
                    for child in node.get('children',[]):walk(child)
                walk(layout)
                self.assertEqual(nodes['icon_coin']['size'],[32,32])
                self.assertEqual(nodes['img_hit_area']['size'],[64,64])
                project=folder/'client';project.mkdir()
                result=export_feature(adapter,path,project,project/'assets/ui',export_only=True,records_dir=folder/'records')
                import json
                prefab=json.loads(Path(result['prefabs'][0]).read_text())
                self.assertEqual([prefab['width'],prefab['height']],[256,384])
                self.assertTrue(prefab['clipping'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_multiple_pages_keep_original_bounds_and_reject_document_canvas(self):
        with tempfile.TemporaryDirectory() as directory:
            path=make_psd(Path(directory)/'Multi.psd',pages=('FirstPanel','SecondPanel'))
            with PSDSource(trim_static_smartobjects=True) as adapter:
                plans=make_plans(adapter.open(path))
                self.assertEqual([layout['size'] for _,layout in plans],[[256,384],[256,384]])
            with PSDSource(page_canvas=True) as adapter:
                with self.assertRaisesRegex(ValueError,'单页面根'):
                    adapter.open(path)

    @unittest.skipUnless(PAGE_FIXTURE.exists(),'Optional real user cache-padding regression fixture')
    def test_club_root_and_shop_geometry_while_icons_and_source_stay_intact(self):
        before=hashlib.sha256(PAGE_FIXTURE.read_bytes()).hexdigest()
        with PSDSource(page_canvas=True,trim_static_smartobjects=True) as adapter:
            snapshot=adapter.open(PAGE_FIXTURE)
            _,layout=make_plans(snapshot)[0]
            self.assertEqual(layout['size'],[1080,1920])
            def find(node,name):
                if node['name']==name:return node
                for child in node.get('children',[]):
                    found=find(child,name)
                    if found:return found
            shop=find(layout,'btn_shop')
            self.assertLess(shop['size'][0],200)
            self.assertLess(shop['size'][1],200)
            self.assertEqual(find(shop,'icon')['size'],[128,128])
            self.assertEqual(find(find(layout,'btn_back'),'icon')['size'],[128,128])
        self.assertEqual(hashlib.sha256(PAGE_FIXTURE.read_bytes()).hexdigest(),before)


if __name__=='__main__':unittest.main()
