"""Restore logical Elasticsearch exports into the isolated, non-serving target."""
import argparse
import base64
import copy
import gzip
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
EXPORT = ROOT / 'business-staged/business-export/search'


def index_body(metadata):
    body = copy.deepcopy(metadata)
    settings = body['settings']['index']
    for key in ['uuid', 'version', 'creation_date', 'provided_name', 'history_uuid']:
        settings.pop(key, None)
    assert set(body) <= {'settings', 'mappings', 'aliases'}
    return body


def bulk_bytes(index, rows):
    lines = []
    for row in rows:
        assert row['_index'] == index and '_id' in row and '_source' in row
        identity = {'_index': index, '_id': row['_id']}
        if '_routing' in row:
            identity['routing'] = row['_routing']
        lines.extend([json.dumps({'index': identity}), json.dumps(row['_source'], ensure_ascii=False)])
    return ('\n'.join(lines) + '\n').encode()


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
    obj = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-elasticsearch-1']))[0]
    assert obj['State']['Running']
    ip = obj['NetworkSettings']['Networks']['singux_default']['IPAddress']
    assert ip
    base = 'http://' + ip + ':9200'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {'Content-Type': 'application/json'}
    if env.get('ES_API_KEY'):
        headers['Authorization'] = 'ApiKey ' + env['ES_API_KEY']
    elif env.get('ES_USERNAME') and env.get('ES_PASSWORD'):
        headers['Authorization'] = 'Basic ' + base64.b64encode((env['ES_USERNAME'] + ':' + env['ES_PASSWORD']).encode()).decode()

    def request(path, body=None, method=None, ndjson=False):
        data = body if ndjson else None if body is None else json.dumps(body).encode()
        actual_headers = dict(headers)
        if ndjson:
            actual_headers['Content-Type'] = 'application/x-ndjson'
        req = urllib.request.Request(base + path, data=data, headers=actual_headers, method=method)
        with opener.open(req, timeout=180) as response:
            return json.load(response)

    exported = json.loads((EXPORT / 'result.json').read_text())
    assert exported['status'] == 'LOGICAL_EXPORT_READY' and not exported['errors']
    result_path = ROOT / 'elasticsearch-restore-result.json'
    if args.resume:
        result = json.loads(result_path.read_text())
        assert result['status'] == 'ELASTICSEARCH_RESTORING'
    else:
        assert not result_path.exists()
        result = {'status': 'ELASTICSEARCH_RESTORING', 'ownedIndexes': [], 'verifiedIndexes': [],
                  'documents': 0, 'sourceChanged': False}
    existing = {item['index'] for item in request('/_cat/indices?format=json&h=index') if not item['index'].startswith('.')}
    assert existing <= set(result['ownedIndexes']), 'Refuse pre-existing non-migration indexes'

    def checkpoint():
        temporary = result_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2))
        temporary.replace(result_path)

    checkpoint()
    for entry in exported['elasticsearch']:
        name = entry['index']
        if name in result['verifiedIndexes']:
            continue
        assert '/' not in name and not name.startswith('.')
        encoded = urllib.parse.quote(name, safe='')
        metadata = json.loads((EXPORT / entry['directory'] / 'metadata.json').read_text())[name]
        with gzip.open(EXPORT / entry['directory'] / 'documents.ndjson.gz', 'rt', encoding='utf-8') as file:
            rows = [json.loads(line) for line in file if line.strip()]
        assert len(rows) == entry['count']
        assert len({(row['_id'], row.get('_routing')) for row in rows}) == len(rows)
        if name not in existing:
            if name not in result['ownedIndexes']:
                result['ownedIndexes'].append(name)
            checkpoint()
            created = request('/' + encoded, index_body(metadata), method='PUT')
            assert created['acknowledged']
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            response = request('/_bulk', bulk_bytes(name, batch), method='POST', ndjson=True)
            assert not response.get('errors') and len(response['items']) == len(batch), 'Bulk write failed'
            assert all(200 <= item['index']['status'] < 300 for item in response['items'])
        refreshed = request('/' + encoded + '/_refresh', method='POST')
        assert refreshed['_shards']['failed'] == 0
        assert request('/' + encoded + '/_count')['count'] == len(rows)
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            docs = [{'_id': row['_id'], **({'routing': row['_routing']} if '_routing' in row else {})} for row in batch]
            readback = request('/' + encoded + '/_mget', {'docs': docs}, method='POST')['docs']
            assert len(readback) == len(batch)
            for original, restored in zip(batch, readback):
                assert restored.get('found') and restored['_id'] == original['_id']
                assert restored['_source'] == original['_source'], 'Restored document content mismatch'
        result['verifiedIndexes'].append(name)
        result['documents'] += len(rows)
        checkpoint()
    result.update(status='ELASTICSEARCH_DOCUMENTS_RESTORED', notLatestSourceSnapshot=True)
    checkpoint()
    print(json.dumps({'status': result['status'], 'indexes': len(result['verifiedIndexes']),
                      'documents': result['documents']}), flush=True)


if __name__ == '__main__':
    main()
