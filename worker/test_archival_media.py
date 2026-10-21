"""Episode archive preparation retains actual identity and refreshed source attribution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from prepare_archival_media import prepare_plan


class ArchivalPreparationTests(unittest.TestCase):
    def test_photo_cache_refreshes_changed_source_credit_without_altering_identity(self):
        parent = Path(__file__).resolve().parents[1] / 'out/archival-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root = Path(temp)
            public = root / 'public'
            public.mkdir()
            original = root / 'original.jpg'
            Image.new('RGB', (48, 32), '#778899').save(original)
            catalog = root / 'catalog.json'
            catalog.write_text('{"assets": []}', encoding='utf-8')
            source = {'id': 'photo', 'downloadUrl': 'https://example.org/source.jpg',
                      'original': 'https://example.org/item', 'author': 'First author', 'license': 'Test license'}
            asset = {'key': 'test_photo', 'src': 'assets/images/test/archive.jpg', 'method': 'photo',
                     'sourceId': 'photo', 'reuseFamily': 'actual-photo-one', 'caption': 'A real photo',
                     'changes': 'Editorial framing'}
            plan = root / 'plan.json'
            def save():
                plan.write_text(json.dumps({'namespace': 'test', 'sources': [source], 'assets': [asset]}), encoding='utf-8')
            with patch('prepare_archival_media.download_source', return_value=(original, {'sha256': 'fixed'})):
                save()
                first = prepare_plan(plan, catalog, public, root / 'cache')[0]
                source['author'] = 'Corrected author'
                save()
                second = prepare_plan(plan, catalog, public, root / 'cache')[0]
                self.assertEqual(first['author'], 'First author')
                self.assertEqual(second['author'], 'Corrected author')
                self.assertEqual(second['reuseFamily'], 'actual-photo-one')
                self.assertEqual((second['width'], second['height']), (48, 32))
            asset['src'] = 'assets/images/other/escape.jpg'
            save()
            with self.assertRaisesRegex(ValueError, "episode's folder"):
                prepare_plan(plan, catalog, public, root / 'cache')


if __name__ == '__main__':
    unittest.main()
