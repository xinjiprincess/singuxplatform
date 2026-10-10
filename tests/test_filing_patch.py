import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('filing', ROOT / 'deploy/compliance/patch-index.py')
filing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filing)


class FilingPatchTests(unittest.TestCase):
    def test_preserves_business_script(self):
        source = '<html><head></head><body><div id="root"></div><script src="umi.js"></script></body></html>'
        footer = (ROOT / 'deploy/compliance/footer.html').read_text(encoding='utf-8')
        result = filing.patch(source, footer)
        self.assertIn('<script src="umi.js"></script>', result)
        self.assertEqual(result.count('id="singux-site-filing"'), 1)
        self.assertIn('蜀ICP备2026030409号', result)

    def test_refuses_duplicate(self):
        with self.assertRaises(ValueError):
            filing.patch('<head></head><body id="singux-site-filing"></body>', '')

    def test_refuses_invalid_shell(self):
        with self.assertRaises(ValueError):
            filing.patch('<html></html>', '')


if __name__ == '__main__':
    unittest.main()
