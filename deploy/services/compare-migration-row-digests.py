"""Compare hashed snapshots without printing user details or applying SQL."""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def compare(source, target):
    assert source['status'] == target['status'] == 'ROW_DIGEST_SNAPSHOT_READY'
    assert source['role'] == 'source' and target['role'] == 'target'
    schemas = []
    source_only = sorted(set(source['tables']) - set(target['tables']))
    target_only = sorted(set(target['tables']) - set(source['tables']))
    results = []
    for name in sorted(set(source['tables']) & set(target['tables'])):
        source_columns = [c for c in source['metadata'] if c['schema'] + '.' + c['table'] == name]
        target_columns = [c for c in target['metadata'] if c['schema'] + '.' + c['table'] == name]
        if source_columns != target_columns:
            schemas.append(name)
            continue
        a, b = source['tables'][name], target['tables'][name]
        primary = any(c['primary'] for c in source_columns)
        if primary:
            assert len({key for key, value in a}) == len(a) and len({key for key, value in b}) == len(b)
            a_map, b_map = dict(a), dict(b)
            added = len(a_map.keys() - b_map.keys())
            target_extra = len(b_map.keys() - a_map.keys())
            modified = sum(a_map[key] != b_map[key] for key in a_map.keys() & b_map.keys())
        else:
            a_counts, b_counts = Counter(value for key, value in a), Counter(value for key, value in b)
            added, target_extra = sum((a_counts - b_counts).values()), sum((b_counts - a_counts).values())
            modified = None
        results.append({'table': name, 'sourceRows': len(a), 'targetRows': len(b),
                        'sourceOnlyRows': added, 'targetOnlyRows': target_extra,
                        'changedSharedPrimaryKeys': modified, 'hasPrimaryKey': primary,
                        'equal': added == target_extra == 0 and modified in (0, None)})
    return {'status': 'INCREMENTAL_ROW_DIFFERENCES_AUDITED',
            'sourceSnapshotUtc': source['startedUtc'], 'targetSnapshotUtc': target['startedUtc'],
            'tableResults': results, 'sourceOnlyTables': source_only, 'targetOnlyTables': target_only,
            'schemaDifferences': schemas, 'equalTables': sum(row['equal'] for row in results),
            'differentTables': sum(not row['equal'] for row in results),
            'databaseChanged': False, 'laterSourceWritesApplied': False,
            'safeToBlindOverwrite': False, 'sourceChanged': False,
            'note': 'Target-only keys can be test data or source deletions; two independently timed snapshots cannot distinguish them. Changed rows require baseline/history reconciliation.'}


def main():
    source = json.loads((ROOT / 'tmp/migration-source-row-digests-20261010.json').read_text())
    target = json.loads((ROOT / 'tmp/migration-target-row-digests-20261010.json').read_text())
    result = compare(source, target)
    path = ROOT / 'outputs/migration-incremental-audit-20261010.json'
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != 'tableResults'}, indent=2))
    for row in result['tableResults']:
        if not row['equal']:
            print(json.dumps(row))


if __name__ == '__main__':
    main()
