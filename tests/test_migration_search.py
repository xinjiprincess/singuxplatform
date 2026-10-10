import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'deploy/services/export-migration-search.py'
spec = importlib.util.spec_from_file_location('migration_search', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MigrationSearchTests(unittest.TestCase):
    def test_matching_visible_count(self):
        self.assertIsNone(module.validate_vector_rows([{'id': '1'}], 'id', 1))

    def test_count_discrepancy_is_explicit(self):
        result = module.validate_vector_rows([{'id': '1'}], 'id', 2)
        self.assertEqual(result['aggregateCount'], 2)
        self.assertEqual(result['visibleCount'], 1)

    def test_duplicate_primary_key_refused(self):
        with self.assertRaises(ValueError):
            module.validate_vector_rows([{'id': '1'}, {'id': '1'}], 'id', 2)

    def test_possible_truncation_refused(self):
        with self.assertRaises(ValueError):
            module.validate_vector_rows([], 'id', 16000)

    def test_empty_collection(self):
        self.assertIsNone(module.validate_vector_rows([], 'id', 0))


if __name__ == '__main__':
    unittest.main()
