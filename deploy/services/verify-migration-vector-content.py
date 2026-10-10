"""Read-only field/vector and filtered similarity checks on the target snapshot."""
import gzip
import json
import math
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
EXPORT = ROOT / 'business-staged/business-export/search'


def main():
    assert json.loads((ROOT / 'vector-restore-result.json').read_text())['status'] == 'VISIBLE_VECTORS_RESTORED'
    config = json.loads((ROOT / 'business-staged/business-export/configs/platform-resolved.json').read_text())
    env = config['services']['backend']['environment']
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-milvus-1']))[0]
    ip = container['NetworkSettings']['Networks']['singux_default']['IPAddress']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(path, body):
        request = urllib.request.Request('http://' + ip + ':19530/v2/vectordb/' + path,
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + env['MILVUS_USER'] + ':' + env['MILVUS_PASSWORD']})
        with opener.open(request, timeout=180) as response:
            result = json.load(response)
        assert result.get('code') == 0, 'Vector verification rejected: ' + str(result.get('code'))
        return result['data']

    total = 0
    searched = 0
    collections = []
    exported = json.loads((EXPORT / 'result.json').read_text())
    for entry in exported['milvus']:
        name = entry['collection']
        metadata = json.loads((EXPORT / entry['directory'] / 'metadata.json').read_text())
        primary = next(f['name'] for f in metadata['fields'] if f.get('primaryKey'))
        vector = next(f['name'] for f in metadata['fields'] if f['type'] == 'FloatVector')
        with gzip.open(EXPORT / entry['directory'] / 'rows.json.gz', 'rt') as file:
            rows = json.load(file)
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            ids = [r[primary] for r in batch]
            actual = call('entities/query', {'collectionName': name, 'outputFields': ['*'],
                'filter': primary + ' in ' + json.dumps(ids), 'limit': len(batch), 'consistencyLevel': 'Strong'})
            actual = {str(r[primary]): r for r in actual}
            assert len(actual) == len(batch), 'Batch primary keys differ'
            for row in batch:
                restored = actual[str(row[primary])]
                for field, value in row.items():
                    if field == vector:
                        assert len(restored[field]) == len(value)
                        assert all(math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-6)
                                   for a, b in zip(restored[field], value)), 'Vector content differs'
                    else:
                        assert restored[field] == value, 'Stored field differs'
            total += len(batch)
        if rows:
            row = rows[0]
            found = call('entities/search', {'collectionName': name, 'annsField': vector,
                'data': [row[vector]], 'filter': primary + ' == ' + str(row[primary]),
                'limit': 1, 'outputFields': [primary], 'consistencyLevel': 'Strong',
                'searchParams': {'metricType': 'COSINE', 'params': {}}})
            assert found and str(found[0][primary]) == str(row[primary]), 'Filtered vector search differs'
            searched += 1
        collections.append(name)
    record = {'status': 'VECTOR_CONTENT_AND_SEARCH_VERIFIED', 'collections': len(collections),
              'rows': total, 'filteredSearches': searched, 'floatAbsoluteTolerance': 1e-6,
              'floatRelativeTolerance': 1e-5, 'sourceChanged': False,
              'freshTextEmbeddingTested': False, 'restartPersistenceTested': False,
              'warnings': exported.get('warnings', [])}
    (ROOT / 'vector-content-verification.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({k: record[k] for k in ['status', 'collections', 'rows', 'filteredSearches']}), flush=True)


if __name__ == '__main__':
    main()
