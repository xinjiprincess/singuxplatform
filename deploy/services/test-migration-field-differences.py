"""Verify hashed field auditing does not infer safe merge decisions."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'fields', Path(__file__).with_name('audit-migration-field-differences.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def snapshot(role, rows):
    return {'status': 'ROW_DIGEST_SNAPSHOT_READY', 'role': role,
            'tables': {'app.user': rows}, 'metadata': [
                {'schema': 'app', 'table': 'user', 'column': 'id', 'primary': True},
                {'schema': 'app', 'table': 'user', 'column': 'last_login', 'primary': False}]}


class FieldTests(unittest.TestCase):
    def setUp(self):
        self.source = snapshot('source', [['a', 'source'], ['same', 'equal'], ['new', 'added']])
        self.target = snapshot('target', [['a', 'target'], ['same', 'equal']])
        self.plan = module.make_plan(self.source, self.target)

    def compare(self, a, b):
        source = {'startedUtc': 'source-time', 'tables': {'app.user': a}}
        target = {'startedUtc': 'target-time', 'tables': {'app.user': b}}
        return module.compare_fields(source, target, self.source, self.target, self.plan)

    def test_only_changed_shared_keys_selected(self):
        self.assertEqual(self.plan['app.user']['keys'], ['a'])

    def test_changed_field_names_not_values_reported(self):
        result = self.compare({'a': {'row': 'source', 'fields': ['id-hash', 'secret-a']}},
                              {'a': {'row': 'target', 'fields': ['id-hash', 'secret-b']}})
        row = result['tables'][0]
        self.assertEqual(row['differentColumns'], {'last_login': 1})
        self.assertEqual(row['changedSinceRowAudit'], 0)
        self.assertNotIn('secret-a', str(result))
        self.assertFalse(result['incrementalApplied'])

    def test_concurrent_row_changes_are_flagged(self):
        result = self.compare({'a': {'row': 'later', 'fields': ['id', 'now']}},
                              {'a': {'row': 'target', 'fields': ['id', 'then']}})
        self.assertEqual(result['tables'][0]['changedSinceRowAudit'], 1)

    def test_deleted_record_is_not_marked_for_deletion(self):
        result = self.compare({}, {'a': {'row': 'target', 'fields': ['id', 'then']}})
        self.assertEqual(result['tables'][0]['missingSinceRowAudit'], 1)
        self.assertEqual(result['tables'][0]['differentColumns'], {})

    def test_duplicate_keys_fail_closed(self):
        self.source['tables']['app.user'].append(['a', 'duplicate'])
        with self.assertRaises(AssertionError):
            module.make_plan(self.source, self.target)


if __name__ == '__main__':
    unittest.main()
