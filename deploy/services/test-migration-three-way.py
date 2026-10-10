import importlib.util
import copy
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('compare-migration-three-way.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ClassificationTests(unittest.TestCase):
    def test_updates(self):
        self.assertEqual(audit.classify('a', 'b', 'a'), 'sourceUpdate')
        self.assertEqual(audit.classify('a', 'a', 'b'), 'targetUpdate')
        self.assertEqual(audit.classify('a', 'b', 'c'), 'divergentChange')

    def test_insert_collisions(self):
        self.assertEqual(audit.classify(None, 'b', 'c'), 'insertCollision')
        self.assertEqual(audit.classify(None, 'b', None), 'sourceInsert')
        self.assertEqual(audit.classify(None, None, 'b'), 'targetInsert')

    def test_deletions(self):
        self.assertEqual(audit.classify('a', None, 'a'), 'sourceDelete')
        self.assertEqual(audit.classify('a', 'a', None), 'targetDelete')
        self.assertEqual(audit.classify('a', None, 'b'), 'divergentChange')

    def test_equal(self):
        self.assertEqual(audit.classify('a', 'a', 'a'), 'unchanged')
        self.assertEqual(audit.classify('a', 'b', 'b'), 'sameChangeBoth')
        self.assertEqual(audit.classify('a', None, None), 'sameChangeBoth')

    def test_schema_drift_blocks_row_classification(self):
        base = {'role': 'baseline', 'status': 'ROW_DIGEST_SNAPSHOT_READY',
                'metadata': [{'schema': 'db', 'table': 'users', 'column': 'id', 'primary': True}],
                'tables': {'db.users': [['key', 'old']]}, 'startedUtc': 'baseline'}
        source, target = copy.deepcopy(base), copy.deepcopy(base)
        source.update(role='source', startedUtc='source')
        target.update(role='target', startedUtc='target')
        source['metadata'].append({'schema': 'db', 'table': 'new', 'column': 'id', 'primary': True})
        source['tables']['db.new'] = []
        result = audit.compare(base, source, target)
        self.assertEqual(result['status'], 'THREE_WAY_SCHEMA_REVIEW_REQUIRED')
        self.assertEqual(result['schemaChanges']['source']['addedTables'], ['db.new'])
        self.assertFalse(result['incrementApplied'])
        self.assertNotIn('totals', result)

    def test_column_drift_is_reported(self):
        base = {'role': 'baseline', 'status': 'ROW_DIGEST_SNAPSHOT_READY',
                'metadata': [{'schema': 'db', 'table': 'users', 'column': 'id', 'primary': True}],
                'tables': {'db.users': []}, 'startedUtc': 'baseline'}
        source, target = copy.deepcopy(base), copy.deepcopy(base)
        source.update(role='source', startedUtc='source')
        target.update(role='target', startedUtc='target')
        target['metadata'][0]['type'] = 'bigint'
        result = audit.compare(base, source, target)
        self.assertEqual(result['schemaChanges']['target']['changedTables'], ['db.users'])


if __name__ == '__main__':
    unittest.main()
