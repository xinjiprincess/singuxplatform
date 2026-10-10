"""Regression tests for read-only migration comparisons."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'comparison', Path(__file__).with_name('compare-migration-row-digests.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def snapshot(role, rows, primary=True):
    return {'status': 'ROW_DIGEST_SNAPSHOT_READY', 'role': role,
            'startedUtc': '2026-10-09T22:42:00Z',
            'metadata': [{'schema': 'app', 'table': 'users', 'column': 'id',
                          'primary': primary, 'type': 'bigint'}],
            'tables': {'app.users': rows}}


class ComparisonTests(unittest.TestCase):
    def test_primary_key_changes_and_separate_additions(self):
        result = module.compare(snapshot('source', [['a', 'new'], ['b', 'same']]),
                                snapshot('target', [['a', 'old'], ['c', 'extra']]))
        row = result['tableResults'][0]
        self.assertEqual((row['sourceOnlyRows'], row['targetOnlyRows'],
                          row['changedSharedPrimaryKeys']), (1, 1, 1))
        self.assertFalse(result['safeToBlindOverwrite'])
        self.assertFalse(result['databaseChanged'])

    def test_no_primary_key_preserves_duplicate_counts(self):
        result = module.compare(snapshot('source', [['x', 'x'], ['x', 'x']], False),
                                snapshot('target', [['x', 'x']], False))
        self.assertEqual(result['tableResults'][0]['sourceOnlyRows'], 1)
        self.assertIsNone(result['tableResults'][0]['changedSharedPrimaryKeys'])

    def test_equal_rows_are_order_independent(self):
        rows = [['a', 'one'], ['b', 'two']]
        result = module.compare(snapshot('source', rows), snapshot('target', rows[::-1]))
        self.assertEqual(result['equalTables'], 1)

    def test_schema_mismatch_prevents_row_comparison(self):
        source, target = snapshot('source', []), snapshot('target', [])
        target['metadata'][0]['type'] = 'varchar(255)'
        result = module.compare(source, target)
        self.assertEqual(result['schemaDifferences'], ['app.users'])
        self.assertEqual(result['tableResults'], [])

    def test_missing_tables_reported_separately(self):
        source, target = snapshot('source', []), snapshot('target', [])
        target = copy.deepcopy(target)
        target['tables'] = {'app.other': []}
        result = module.compare(source, target)
        self.assertEqual(result['sourceOnlyTables'], ['app.users'])
        self.assertEqual(result['targetOnlyTables'], ['app.other'])

    def test_duplicate_primary_keys_rejected(self):
        with self.assertRaises(AssertionError):
            module.compare(snapshot('source', [['a', 'x'], ['a', 'y']]),
                           snapshot('target', []))


if __name__ == '__main__':
    unittest.main()
