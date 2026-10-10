"""Online logical exports of Elasticsearch and Milvus; never copy live indexes."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = Path('/data/singux-migration-20261009/search-export-v2')


def request(base, path, body=None, headers=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers=dict({'Content-Type': 'application/json'}, **(headers or {})), method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False))


def validate_vector_rows(rows, primary, aggregate_count):
    if not 0 <= aggregate_count < 16000 or len(rows) >= 16000:
        raise ValueError('Use an iterator; refusing a potentially truncated export')
    if len({str(row[primary]) for row in rows}) != len(rows):
        raise ValueError('Duplicate primary keys in visible rows')
    if len(rows) != aggregate_count:
        return {'reason': 'Aggregate differs from visible unique rows; recheck before cutover.',
                'aggregateCount': aggregate_count, 'visibleCount': len(rows)}
    return None


def main():
    os.umask(0o077)
    resume = '--resume' in sys.argv
    ROOT.mkdir(mode=0o700, exist_ok=resume)
    containers = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1',
                                                     'singux-elasticsearch-1', 'singux-milvus-1']))
    env = dict(x.split('=', 1) for x in containers[0]['Config']['Env'])
    def ip(obj):
        return next(x['IPAddress'] for x in obj['NetworkSettings']['Networks'].values() if x.get('IPAddress'))
    es = 'http://' + ip(containers[1]) + ':9200'
    milvus = 'http://' + ip(containers[2]) + ':19530'
    es_headers = {}
    if env.get('ES_API_KEY'):
        es_headers['Authorization'] = 'ApiKey ' + env['ES_API_KEY']
    elif env.get('ES_USERNAME') and env.get('ES_PASSWORD'):
        es_headers['Authorization'] = 'Basic ' + base64.b64encode((env['ES_USERNAME'] + ':' + env['ES_PASSWORD']).encode()).decode()
    vector_headers = {'Authorization': 'Bearer ' + env.get('MILVUS_USER', '') + ':' + env.get('MILVUS_PASSWORD', '')}
    report = {'status': 'EXPORTING', 'elasticsearch': [], 'milvus': [], 'errors': [], 'warnings': [],
              'crossStoreConsistent': False, 'sourceWritesPaused': False}
    if resume:
        report = json.loads((ROOT / 'result.json').read_text())
        report['errors'] = []
    def checkpoint():
        dump(ROOT / 'result.json', report)
    for entry in request(es, '/_cat/indices?format=json&h=index', headers=es_headers):
        name = entry['index']
        if name.startswith('.'):
            continue
        if any(item['index'] == name for item in report['elasticsearch']):
            continue
        encoded = urllib.parse.quote(name, safe='')
        directory = ROOT / ('es-' + hashlib.sha256(name.encode()).hexdigest()[:16])
        directory.mkdir()
        dump(directory / 'metadata.json', request(es, '/' + encoded, headers=es_headers))
        scroll = None
        try:
            batch = request(es, '/' + encoded + '/_search?scroll=5m',
                            {'size': 500, 'sort': ['_doc'], 'track_total_hits': True, 'query': {'match_all': {}}}, es_headers)
            expected = batch['hits']['total']['value']
            count = 0
            with gzip.open(directory / 'documents.ndjson.gz', 'wt', encoding='utf-8') as output:
                while True:
                    scroll = batch.get('_scroll_id')
                    hits = batch['hits']['hits']
                    if not hits:
                        break
                    for hit in hits:
                        output.write(json.dumps(hit, ensure_ascii=False) + '\n')
                        count += 1
                    batch = request(es, '/_search/scroll', {'scroll': '5m', 'scroll_id': scroll}, es_headers)
            assert count == expected, 'Scroll export count mismatch'
            report['elasticsearch'].append({'index': name, 'count': count, 'directory': directory.name})
        except Exception as exc:
            report['errors'].append({'store': 'elasticsearch', 'name': name, 'errorType': type(exc).__name__})
        finally:
            if scroll:
                request(es, '/_search/scroll', {'scroll_id': [scroll]}, es_headers, method='DELETE')
        checkpoint()
    def vector(path, body):
        response = request(milvus, '/v2/vectordb/' + path, body, vector_headers)
        if response.get('code') != 0:
            raise ValueError('Milvus API rejected operation: ' + str(response.get('code')))
        return response['data']
    names = vector('collections/list', {})
    for name in names:
        if any(item['collection'] == name for item in report['milvus']):
            continue
        directory = ROOT / ('milvus-' + hashlib.sha256(name.encode()).hexdigest()[:16])
        directory.mkdir(exist_ok=resume)
        try:
            params = {'collectionName': name}
            description = vector('collections/describe', params)
            dump(directory / 'metadata.json', description)
            query = dict(params, outputFields=['count(*)'], filter='', consistencyLevel='Strong')
            try:
                counts = vector('entities/query', query)
            except ValueError as exc:
                if str(exc) != 'Milvus API rejected operation: 101':
                    raise
                stats = vector('collections/get_stats', params)
                if stats['rowCount'] == 0 and not description.get('indexes'):
                    with gzip.open(directory / 'rows.json.gz', 'wt', encoding='utf-8') as output:
                        json.dump([], output)
                    report['milvus'].append({'collection': name, 'count': 0, 'directory': directory.name,
                                             'verification': 'unloaded_unindexed_stats_only'})
                    report['warnings'].append({'collection': name, 'reason': 'No index; rowCount reports zero. Recheck/rebuild before cutover.'})
                    checkpoint()
                    continue
                vector('collections/load', params)
                counts = vector('entities/query', query)
            expected = counts[0]['count(*)']
            assert 0 <= expected < 16000, 'Use SDK iterator for larger collections; refuse truncation'
            fields = [f.get('name', f.get('fieldName')) for f in description['fields']]
            rows = [] if expected == 0 else vector('entities/query', dict(params, outputFields=fields + ['*'],
                                                                         filter='', limit=16000, consistencyLevel='Strong'))
            primary = next(f.get('name', f.get('fieldName')) for f in description['fields'] if f.get('primaryKey') or f.get('isPrimary'))
            warning = validate_vector_rows(rows, primary, expected)
            if warning:
                report['warnings'].append(dict(warning, collection=name))
            with gzip.open(directory / 'rows.json.gz', 'wt', encoding='utf-8') as output:
                json.dump(rows, output, ensure_ascii=False)
            report['milvus'].append({'collection': name, 'count': len(rows), 'aggregateCount': expected, 'directory': directory.name})
        except Exception as exc:
            report['errors'].append({'store': 'milvus', 'name': name, 'errorType': type(exc).__name__})
        checkpoint()
    report['status'] = 'LOGICAL_EXPORT_READY' if not report['errors'] else 'LOGICAL_EXPORT_INCOMPLETE'
    checkpoint()
    print(json.dumps(report), flush=True)
    assert not report['errors'], 'Do not restore an incomplete export as a completed migration'


if __name__ == '__main__':
    main()
