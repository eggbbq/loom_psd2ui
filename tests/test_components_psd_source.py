import os
"""Verify actual PSD/PSB decoding and compositing through psd-tools."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from psd_tools import PSDImage

from tests.component_fixtures import make_psd, make_text_psd
from psd2ui.psd.source import PSDSource
from psd2ui.ui.exporter import make_plans

ROOT = Path(__file__).resolve().parents[1]
PROVIDED = Path(os.environ.get('PSD2UI_COMPLEX_PSD_FIXTURE',ROOT/'tests/fixtures/complex_type.psd'))


def walk(node):
    yield node
    for child in node.get('children', []):
        yield from walk(child)


def named(snapshot, name):
    return next(node for node in walk(snapshot['tree']) if node['name'] == name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PSDSourceTests(unittest.TestCase):
    def test_real_psd_and_psb_parse_to_identical_named_page_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for version, extension in ((1, 'psd'), (2, 'psb')):
                with self.subTest(version=version):
                    path = make_psd(folder/f'Fixture.{extension}', version=version)
                    before = sha(path)
                    with PSDSource() as source:
                        snapshot = source.open(path)
                        self.assertEqual(snapshot['dpi'], 72)
                        self.assertEqual(snapshot['tree']['kind'], 'DocumentNode')
                        root = named(snapshot, 'FixturePanel')
                        self.assertEqual(root['box'], [0, 0, 256, 384])
                        self.assertEqual(named(snapshot, 'icon_coin')['box'][2:], [32, 32])
                        self.assertFalse(named(snapshot, 'on')['visible'])
                        self.assertTrue(named(snapshot, 'image_on')['visible'])
                        plans = make_plans(snapshot)
                        self.assertEqual(len(plans), 1)
                        self.assertEqual(plans[0][1]['name'], 'FixturePanel')
                        self.assertNotIn('#draft', [n['name'] for n in walk(plans[0][1])])
                    self.assertEqual(sha(path), before)

    def test_target_only_render_respects_hidden_children_and_excludes_siblings(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); path = make_psd(folder/'Fixture.psd')
            before = sha(path)
            with PSDSource() as source:
                snapshot = source.open(path)
                for name, expected_color in (('image_on', (51, 221, 51, 255)),
                                             ('image_off', (221, 51, 51, 255))):
                    node = named(snapshot, name); output = folder/(name+'.png')
                    source.script({'path': str(path), 'session': snapshot['session'], 'action': 'render',
                                   'jobs': [{'indices': node['indices'], 'name': name, 'output': str(output)}]})
                    with Image.open(output) as image:
                        self.assertEqual(image.size, (48, 16))
                        self.assertEqual(image.convert('RGBA').getpixel((0, 0)), expected_color)
                node = named(snapshot, 'switch_sound'); output = folder/'switch.png'
                source.script({'path': str(path), 'session': snapshot['session'], 'action': 'render',
                               'jobs': [{'indices': node['indices'], 'name': node['name'], 'output': str(output)}]})
                with Image.open(output) as image:
                    self.assertEqual(image.size, (80, 32))
                    self.assertEqual(image.convert('RGBA').getpixel((20, 12)), (221, 51, 51, 255))
                self.assertEqual(source.script({'path': str(path), 'session': snapshot['session'], 'action': 'inspect'}), snapshot)
            self.assertEqual(sha(path), before)

    def test_icon_export_keeps_full_transparent_canvas(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); path = make_psd(folder/'Fixture.psd')
            with PSDSource() as source:
                snapshot = source.open(path); node = named(snapshot, 'icon_coin')
                output = folder/'icon.png'
                source.script({'path': str(path), 'session': snapshot['session'], 'action': 'render',
                               'jobs': [{'indices': node['indices'], 'name': node['name'], 'output': str(output)}]})
                with Image.open(output) as image:
                    self.assertEqual(image.size, (32, 32))
                    self.assertEqual(image.convert('RGBA').getpixel((0, 0))[3], 0)
                    self.assertEqual(image.convert('RGBA').getpixel((16, 16)), (255, 255, 0, 255))

    def test_isolated_cut_keeps_own_opacity_without_double_applying_ancestors(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); path = make_psd(folder/'Fixture.psd')
            document = PSDImage.open(path)
            content = document[0][1]
            switch = next(layer for layer in content if layer.name == 'switch_sound')
            off = next(layer for layer in switch if layer.name == 'off')
            switch.visible = False
            switch.opacity = 128
            off.visible = False
            off.opacity = 128
            off[0].opacity = 128
            document.save(path)
            before = sha(path)
            with PSDSource() as source:
                snapshot = source.open(path); node = named(snapshot, 'off')
                output = folder/'off.png'
                source.script({'path':str(path),'session':snapshot['session'],'action':'render',
                    'jobs':[{'indices':node['indices'],'name':'off','output':str(output)}]})
                with Image.open(output) as image:
                    self.assertEqual(image.convert('RGBA').getpixel((0, 0))[3], 64)
                live_switch = next(layer for layer in source.psd[0][1] if layer.name == 'switch_sound')
                live_off = next(layer for layer in live_switch if layer.name == 'off')
                self.assertFalse(live_switch.visible)
                self.assertFalse(live_off.visible)
            self.assertEqual(sha(path), before)

    def test_multiple_page_roots_keep_absolute_geometry_and_layer_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = make_psd(Path(directory)/'Multiple.psd', pages=('FirstPanel', 'SecondPanel'))
            with PSDSource() as source:
                snapshot = source.open(path)
                self.assertEqual([n['name'] for n in snapshot['tree']['children']], ['FirstPanel', 'SecondPanel'])
                self.assertEqual(named(snapshot, 'SecondPanel')['box'], [256, 0, 256, 384])
                plans = make_plans(snapshot)
                self.assertEqual([layout['name'] for _, layout in plans], ['FirstPanel', 'SecondPanel'])

    def test_changed_source_is_rejected_before_using_stale_layer_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = make_psd(Path(directory)/'Fixture.psd')
            with PSDSource() as source:
                snapshot = source.open(path)
                path.write_bytes(path.read_bytes()+b'changed')
                with self.assertRaises(ValueError):
                    source.script({'path': str(path), 'session': snapshot['session'], 'action': 'inspect'})

    def test_render_failures_restore_real_layer_flags_and_source_file(self):
        for failure in ('psd2ui.psd.pixels.composite_pil', 'PIL.Image.Image.save'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory); path = make_psd(folder/'Fixture.psd')
                document = PSDImage.open(path)
                control = next(layer for layer in document[0][1] if layer.name == 'switch_sound')
                control.visible = False
                document.save(path)
                before = sha(path)
                with PSDSource() as source:
                    snapshot = source.open(path); node = named(snapshot, 'image_on')
                    before_flags = [(layer.name, layer.visible, layer.opacity) for layer in source.psd.descendants()]
                    request = {'path':str(path),'session':snapshot['session'],'action':'render',
                        'jobs':[{'indices':node['indices'],'name':'image_on','output':str(folder/'on.png')}]}
                    with patch(failure, side_effect=OSError('Injected renderer failure')):
                        with self.assertRaises(OSError):
                            source.script(request)
                    self.assertEqual([(layer.name, layer.visible, layer.opacity) for layer in source.psd.descendants()], before_flags)
                    source.script(request)
                    self.assertTrue((folder/'on.png').is_file())
                    self.assertEqual([(layer.name, layer.visible, layer.opacity) for layer in source.psd.descendants()], before_flags)
                self.assertEqual(sha(path), before)

    @unittest.skipUnless(PROVIDED.is_file(), 'User-provided PSD is optional outside this workspace')
    def test_provided_real_psd_text_is_editable_and_source_remains_unchanged(self):
        before = sha(PROVIDED)
        with PSDSource() as source:
            snapshot = source.open(PROVIDED)
            text = [n for n in walk(snapshot['tree']) if 'text' in n]
            self.assertEqual(len(text), 39)
            first = next(n for n in text if n['text'].strip() == '99/96')
            self.assertEqual(first['fontSize'], 30)
            self.assertTrue(first['font'])
            self.assertEqual(first['align'], 'left')
            with self.assertRaises(ValueError):
                make_plans(snapshot)  # Legacy Chinese roots have not been renamed to the agreed contract.
        self.assertEqual(sha(PROVIDED), before)

    @unittest.skipUnless(PROVIDED.is_file(), 'Real type fixture needs user-provided PSD type records')
    def test_real_type_records_can_be_parsed_under_current_component_names(self):
        before = sha(PROVIDED)
        with tempfile.TemporaryDirectory() as directory:
            path, expected = make_text_psd(Path(directory)/'Text.psd', PROVIDED)
            with PSDSource() as source:
                snapshot = source.open(path)
                titles = [n for n in walk(snapshot['tree']) if n['name'] == 'title']
                self.assertEqual(len(titles), 2)
                self.assertTrue(all(n['text'].rstrip('\r') == expected.rstrip('\r') for n in titles))
                self.assertEqual(len(make_plans(snapshot)), 1)
        self.assertEqual(sha(PROVIDED), before)


if __name__ == '__main__':
    unittest.main()
