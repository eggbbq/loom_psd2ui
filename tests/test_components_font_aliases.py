import os
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tests.component_fixtures import make_text_psd
from psd2ui.psd.source import PSDSource
from psd2ui.ui.exporter import export_feature
from psd2ui.ui.font_aliases import validate_font_aliases,apply_font_aliases,automatic_font_aliases

ROOT=Path(__file__).resolve().parents[1]
OPTIONAL_TYPE_FIXTURE=Path(os.environ.get('PSD2UI_COMPLEX_PSD_FIXTURE',ROOT/'tests/fixtures/complex_type.psd'))


class FontAliasTests(unittest.TestCase):
    def test_automatic_alias_aggregates_scripts_independent_of_layer_order(self):
        nodes=[dict(name='zh',font='MissingFamily-Bold',text='成员'),dict(name='number',font='MissingFamily-Bold',text='12345')]
        first=automatic_font_aliases(dict(tree=dict(children=nodes)),families=['Arial','PingFang SC'])
        second=automatic_font_aliases(dict(tree=dict(children=list(reversed(nodes)))),families=['Arial','PingFang SC'])
        self.assertEqual(first,second)
        self.assertEqual(first['MissingFamily-Bold'],dict(family='PingFang SC',bold=True))
    def test_alias_is_explicit_and_only_changes_editable_text(self):
        layout=dict(name='Page',type='root',children=[
            dict(name='title',type='text',font='Source-Bold',text='文字'),
            dict(name='other',type='text',font='Other'),
            dict(name='img_title',type='image',font='Source-Bold')])
        original=copy.deepcopy(layout)
        self.assertEqual(apply_font_aliases(layout,{}),[])
        self.assertEqual(layout,original)
        changes=apply_font_aliases(layout,validate_font_aliases({'Source-Bold':{'family':'PingFang SC','bold':True}}))
        self.assertEqual(len(changes),1)
        self.assertEqual(layout['children'][0]['font'],'PingFang SC')
        self.assertTrue(layout['children'][0]['bold'])
        self.assertEqual(layout['children'][0]['fontAliasSource'],'Source-Bold')
        self.assertEqual(layout['children'][1:],original['children'][1:])

    def test_rejects_ambiguous_alias_config(self):
        for config in ([],{'A':{'bold':True}},{'A':{'family':'B','bold':'true'}},{'A':{'family':'B','size':24}}):
            with self.subTest(config=config),self.assertRaises(ValueError):validate_font_aliases(config)

    @unittest.skipUnless(OPTIONAL_TYPE_FIXTURE.exists(),'Requires optional real type fixture')
    def test_export_serializes_family_and_bold_but_native_retains_source_font(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source,_=make_text_psd(folder/'Text.psd',OPTIONAL_TYPE_FIXTURE)
            project=folder/'client';project.mkdir()
            with PSDSource() as adapter:
                snapshot=adapter.open(source)
                def nodes(n):
                    yield n
                    for c in n.get('children',[]):yield from nodes(c)
                original_font=next(x['font'] for x in nodes(snapshot['tree']) if 'text' in x)
                result=export_feature(adapter,source,project,project/'assets/ui',export_only=True,
                    records_dir=folder/'records',font_aliases={original_font:{'family':'PingFang SC','bold':True}})
            prefab=json.loads(Path(result['prefabs'][0]).read_text())
            def widgets(n):
                yield n
                for c in n.get('_$child',[]):yield from widgets(c)
            fields=[x for x in widgets(prefab) if x['_$type'] in ('GTextField','GTextInput')]
            self.assertTrue(fields)
            self.assertTrue(all(x['font']=='PingFang SC' and x['bold'] is True for x in fields))
            native=json.loads((folder/'records/Text/native.json').read_text())
            self.assertTrue(all(x['font']==original_font for x in nodes(native['tree']) if 'text' in x))
            record=json.loads((folder/'records/Text/psd.json').read_text())
            self.assertTrue(record['fontAliasApplications'])


if __name__=='__main__':unittest.main()
