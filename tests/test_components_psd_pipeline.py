import os
"""End-to-end real PSD extraction into production-shaped Laya files."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from tests.component_fixtures import make_psd, make_text_psd
from psd2ui.psd.source import PSDSource
from psd2ui.ui.exporter import export_feature

ROOT = Path(__file__).resolve().parents[1]
PROVIDED = Path(os.environ.get('PSD2UI_COMPLEX_PSD_FIXTURE',ROOT/'tests/fixtures/complex_type.psd'))


def nodes(node):
    yield node
    for child in node.get('_$child', []):
        yield from nodes(child)


def named(prefab, name):
    return next(node for node in nodes(prefab) if node.get('name') == name)


def identities(directory):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


class PSDPipelineTests(unittest.TestCase):
    def test_real_psd_exports_current_components_and_only_final_laya_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = make_psd(root/'Fixture.psd')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            project = root/'client'; project.mkdir(); assets = project/'assets/ui'
            with PSDSource() as adapter:
                result = export_feature(adapter, source, project, assets,
                                        export_only=True, records_dir=root/'records')
            prefab = json.loads((assets/'prefabs/FixturePanel.lh').read_text())
            self.assertEqual(prefab['_$type'], 'GWidget')
            self.assertEqual(named(prefab, 'btn_login')['_$type'], 'GButton')
            self.assertEqual(named(prefab, 'btn_login')['downEffect'], 1)
            control = named(prefab, 'switch_sound')
            self.assertEqual(control['_$type'], 'GButton')
            self.assertEqual(control['mode'], 1)
            self.assertFalse(control['selected'])
            self.assertEqual(control['downEffect'], 0)
            states = {c['name']:c for c in control['_$child']}
            self.assertEqual(states['on']['gears'][0]['pages'], [1])
            self.assertEqual(states['off']['gears'][0]['pages'], [0])
            self.assertEqual(named(prefab, 'list_tasks_node')['_$type'], 'GWidget')
            listing = named(prefab, 'list_tasks')
            self.assertEqual(listing['_$type'], 'GList')
            self.assertEqual(listing['_initItemNum'], 3)
            self.assertTrue(listing['_isDemo'])
            self.assertEqual(listing['scroller']['barDisplay'], 5)
            self.assertEqual(listing['scroller']['touchEffect'], 1)
            cells = [c for c in listing['_$child'] if c['name'].startswith('item_')]
            self.assertEqual([c['name'] for c in cells], ['item_1'])
            self.assertEqual(listing['_templateNode']['_$ref'], cells[0]['_$id'])
            self.assertEqual(listing['_templateNode']['_$tmpl'], 'itemTemplate')
            self.assertEqual(named(prefab, 'icon_coin')['_$type'], 'GLoader')
            self.assertEqual([named(prefab, 'icon_coin')[d] for d in ('width','height')], [32,32])
            self.assertFalse(any('#' in n.get('name', '') for n in nodes(prefab)))
            self.assertEqual(sorted(p.name for p in assets.iterdir()), ['images','prefabs'])
            files = [p for p in assets.rglob('*') if p.is_file()]
            self.assertTrue(all(p.suffix in ('.png','.lh','.meta') for p in files))
            for image in (assets/'images').glob('*.png'):
                self.assertRegex(image.name, r'^.+@[0-9a-z]{13}\.png$')
                meta = json.loads(Path(str(image)+'.meta').read_text())
                self.assertEqual(meta['importer']['textureType'], 2)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
            self.assertEqual(result['warnings'], [])

    def test_reexport_keeps_resource_uuids_and_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = make_psd(root/'Fixture.psd')
            project = root/'client'; project.mkdir(); assets = project/'assets/ui'
            with PSDSource() as adapter:
                export_feature(adapter, source, project, assets, export_only=True, records_dir=root/'records')
                before = identities(assets)
                export_feature(adapter, source, project, assets, export_only=True, records_dir=root/'records')
            self.assertEqual(identities(assets), before)

    @unittest.skipUnless(PROVIDED.is_file(), 'Real type fixture needs user-provided PSD type records')
    def test_actual_psd_type_layers_map_to_input_padding_and_button_title(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, text = make_text_psd(root/'Text.psd', PROVIDED)
            project = root/'client'; project.mkdir(); assets = project/'assets/ui'
            with PSDSource() as adapter:
                export_feature(adapter, source, project, assets, export_only=True, records_dir=root/'records')
            prefab = json.loads((assets/'prefabs/TextPanel.lh').read_text())
            wrapper, field = named(prefab, 'input_password_node'), named(prefab, 'input_password')
            self.assertEqual(wrapper['_$type'], 'GWidget')
            self.assertEqual(field['_$type'], 'GTextInput')
            self.assertEqual(field['prompt'], text)
            self.assertEqual(field['text'], '')
            self.assertEqual(field.get('x', 0), 0)
            self.assertEqual(field.get('y', 0), 0)
            self.assertEqual([field[k] for k in ('width','height')], [wrapper[k] for k in ('width','height')])
            self.assertTrue(any(field['padding']))
            self.assertNotIn('placeholder', [c['name'] for c in wrapper['_$child']])
            button = named(prefab, 'btn_login')
            self.assertEqual(button['title'], text)
            self.assertEqual(button['titleWidget']['_$ref'], named(button, 'title')['_$id'])

    def test_layer_render_does_not_start_external_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = make_psd(root/'Fixture.psd')
            project = root/'client'; project.mkdir()
            with patch('subprocess.Popen', side_effect=AssertionError('No rendering application may be launched')):
                with PSDSource() as adapter:
                    export_feature(adapter, source, project, project/'assets/ui',
                                   export_only=True, records_dir=root/'records')


if __name__ == '__main__':
    unittest.main()
