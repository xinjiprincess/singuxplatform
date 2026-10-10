import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('uploads', Path(__file__).resolve().parents[1] / 'deploy/services/restore-migration-uploads.py')
uploads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploads)


class UploadInventoryTests(unittest.TestCase):
    def test_inventory_nested_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            (root / 'nested/file.txt').write_bytes(b'upload')
            self.assertEqual(uploads.inventory(root), {'nested/file.txt': {
                'bytes': 6, 'sha256': hashlib.sha256(b'upload').hexdigest()}})

    def test_detect_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'file.txt'
            path.write_bytes(b'first')
            before = uploads.inventory(root)
            path.write_bytes(b'other')
            self.assertNotEqual(uploads.inventory(root), before)


if __name__ == '__main__':
    unittest.main()
