"""Restore exported visible Milvus rows to the isolated target, never the source."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
EXPORT = ROOT / 'business-staged/business-export/search'


def create_body(description):
    assert not description.get('autoId'), 'Explicit IDs required for safe restore'
    assert not description.get('aliases') and not description.get('functions'), 'Unsupported schema extensions'
    fields = []
    types = {}
    for source in description['fields']:
        assert source['type'] in {'Int64', 'VarChar', 'FloatVector'}, 'Unsupported field type'
        assert not source.get('nullable') and not source.get('partitionKey')
        types[source['name']] = source['type']
        field = {'fieldName': source['name'], 'dataType': source['type'],
                 'isPrimary': source.get('primaryKey', False)}
        params = {item['key']: item['value'] for item in source.get('params', [])}
        if params:
            field['elementTypeParams'] = params
        fields.append(field)
    indexes = []
    for source in description.get('indexes', []):
        index = {'fieldName': source['fieldName'], 'indexName': source['indexName'],
                 'params': {'index_type': 'AUTOINDEX'}}
        if types[source['fieldName']] == 'FloatVector':
            index['metricType'] = source['metricType']
        indexes.append(index)
    return {'collectionName': description['collectionName'],
            'schema': {'autoID': False, 'enableDynamicField': description.get('enableDynamicField', False), 'fields': fields},
            'indexParams': indexes,
            'params': {'shardsNum': description.get('shardsNum', 1), 'consistencyLevel': 'Strong'}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert 'singux-backend-1' not in subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True).splitlines()
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal']
    config = json.loads((ROOT / 'business-staged/business-export/configs/platform-resolved.json').read_text())
    env = config['services']['backend']['environment']
    obj = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-milvus-1']))[0]
    assert obj['State']['Running']
    ip = obj['NetworkSettings']['Networks']['singux_default']['IPAddress']
    assert ip
    base = 'http://' + ip + ':19530/v2/vectordb/'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(path, body):
        request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                    headers={'Content-Type': 'application/json',
                             'Authorization': 'Bearer ' + env['MILVUS_USER'] + ':' + env['MILVUS_PASSWORD']})
        with opener.open(request, timeout=180) as response:
            result = json.load(response)
        assert result.get('code') == 0, 'Milvus restore operation rejected: ' + str(result.get('code'))
        return result['data']

    exported = json.loads((EXPORT / 'result.json').read_text())
    assert exported['status'] == 'LOGICAL_EXPORT_READY' and not exported['errors']
    result_path = ROOT / 'vector-restore-result.json'
    if args.resume:
        result = json.loads(result_path.read_text())
        assert result['status'] == 'VECTOR_RESTORING'
    else:
        assert not result_path.exists()
        result = {'status': 'VECTOR_RESTORING', 'ownedCollections': [], 'verifiedCollections': [],
                  'visibleRows': 0, 'warnings': exported.get('warnings', []), 'sourceChanged': False}
    existing = set(call('collections/list', {}))
    assert existing <= set(result['ownedCollections']), 'Refuse pre-existing non-migration collections'

    def checkpoint():
        temporary = result_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2))
        temporary.replace(result_path)

    checkpoint()
    for entry in exported['milvus']:
        name = entry['collection']
        if name in result['verifiedCollections']:
            continue
        metadata = json.loads((EXPORT / entry['directory'] / 'metadata.json').read_text())
        assert metadata['collectionName'] == name
        with gzip.open(EXPORT / entry['directory'] / 'rows.json.gz', 'rt', encoding='utf-8') as file:
            rows = json.load(file)
        assert len(rows) == entry['count'] and len(rows) < 16000
        primary = next(field['name'] for field in metadata['fields'] if field.get('primaryKey'))
        assert len({str(row[primary]) for row in rows}) == len(rows)
        if name not in existing:
            if name not in result['ownedCollections']:
                result['ownedCollections'].append(name)
            checkpoint()
            call('collections/create', create_body(metadata))
        for start in range(0, len(rows), 50):
            call('entities/upsert', {'collectionName': name, 'data': rows[start:start + 50]})
        call('collections/flush', {'collectionName': name})
        call('collections/load', {'collectionName': name})
        restored = call('entities/query', {'collectionName': name, 'outputFields': [primary],
                        'filter': '', 'limit': 16000, 'consistencyLevel': 'Strong'})
        assert {str(row[primary]) for row in restored} == {str(row[primary]) for row in rows}
        assert len(restored) == len(rows), 'Restored visible count differs'
        result['verifiedCollections'].append(name)
        result['visibleRows'] += len(rows)
        checkpoint()
    result['status'] = 'VISIBLE_VECTORS_RESTORED'
    result['notLatestSourceSnapshot'] = True
    checkpoint()
    print(json.dumps({'status': result['status'], 'collections': len(result['verifiedCollections']),
                      'visibleRows': result['visibleRows'], 'warnings': len(result['warnings'])}), flush=True)


if __name__ == '__main__':
    main()
