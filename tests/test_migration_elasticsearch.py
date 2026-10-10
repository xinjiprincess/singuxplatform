import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('restore_es', Path(__file__).resolve().parents[1] / 'deploy/services/restore-migration-elasticsearch.py')
es = importlib.util.module_from_spec(spec)
spec.loader.exec_module(es)


class ElasticsearchRestoreTests(unittest.TestCase):
    def test_drop_generated_settings_only(self):
        source = {'settings': {'index': {'uuid': 'source', 'version': {'created': '8'},
                  'creation_date': '123', 'provided_name': 'knowledge', 'number_of_shards': '3',
                  'number_of_replicas': '1'}}, 'mappings': {'properties': {'content': {'type': 'text'}}}, 'aliases': {}}
        result = es.index_body(source)
        self.assertNotIn('uuid', result['settings']['index'])
        self.assertEqual(result['settings']['index']['number_of_shards'], '3')
        self.assertEqual(result['mappings'], source['mappings'])
        self.assertIn('uuid', source['settings']['index'])

    def test_preserve_id_routing_and_source(self):
        rows = [{'_index': 'knowledge', '_id': '123', '_routing': 'tenant-1', '_source': {'text': 'abc'}}]
        data = es.bulk_bytes('knowledge', rows)
        self.assertTrue(data.endswith(b'\n'))
        lines = data.decode().splitlines()
        self.assertEqual(json.loads(lines[0])['index'], {'_index': 'knowledge', '_id': '123', 'routing': 'tenant-1'})
        self.assertEqual(json.loads(lines[1]), rows[0]['_source'])

    def test_refuse_wrong_index(self):
        with self.assertRaises(AssertionError):
            es.bulk_bytes('knowledge', [{'_index': 'other', '_id': '1', '_source': {}}])


if __name__ == '__main__':
    unittest.main()
