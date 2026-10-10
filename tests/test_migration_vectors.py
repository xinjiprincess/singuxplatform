import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('vectors', Path(__file__).resolve().parents[1] / 'deploy/services/restore-migration-vectors.py')
vectors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vectors)


class SchemaTests(unittest.TestCase):
    def metadata(self):
        return {'collectionName': 'kb_18', 'autoId': False, 'fields': [
            {'name': 'qa_id', 'type': 'Int64', 'primaryKey': True},
            {'name': 'question', 'type': 'VarChar', 'params': [{'key': 'max_length', 'value': '65535'}]},
            {'name': 'vector', 'type': 'FloatVector', 'params': [{'key': 'dim', 'value': '1536'}]}],
            'indexes': [{'fieldName': 'qa_id', 'indexName': 'index_id', 'metricType': 'COSINE'},
                        {'fieldName': 'vector', 'indexName': 'index_vector', 'metricType': 'COSINE'}]}

    def test_preserve_schema_and_only_vector_metric(self):
        original = self.metadata()
        unchanged = copy.deepcopy(original)
        result = vectors.create_body(original)
        self.assertFalse(result['schema']['autoID'])
        self.assertTrue(result['schema']['fields'][0]['isPrimary'])
        self.assertEqual(result['schema']['fields'][2]['elementTypeParams']['dim'], '1536')
        self.assertNotIn('metricType', result['indexParams'][0])
        self.assertEqual(result['indexParams'][1]['metricType'], 'COSINE')
        self.assertEqual(original, unchanged)

    def test_refuse_auto_id_reassignment(self):
        metadata = self.metadata()
        metadata['autoId'] = True
        with self.assertRaises(AssertionError):
            vectors.create_body(metadata)

    def test_refuse_unsupported_schema(self):
        metadata = self.metadata()
        metadata['fields'][0]['type'] = 'Array'
        with self.assertRaises(AssertionError):
            vectors.create_body(metadata)


if __name__ == '__main__':
    unittest.main()
