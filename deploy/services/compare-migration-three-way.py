"""Classify immutable-baseline/source/target digests, never apply row changes."""
from collections import Counter
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def classify(base, source, target):
    if source == target:
        return 'unchanged' if source == base else 'sameChangeBoth'
    if target == base:
        return 'sourceInsert' if base is None else ('sourceDelete' if source is None else 'sourceUpdate')
    if source == base:
        return 'targetInsert' if base is None else ('targetDelete' if target is None else 'targetUpdate')
    return 'insertCollision' if base is None else 'divergentChange'


def compare(base, source, target):
    snapshots = [base, source, target]
    assert [s['role'] for s in snapshots] == ['baseline', 'source', 'target']
    assert all(s['status'] == 'ROW_DIGEST_SNAPSHOT_READY' for s in snapshots)
    if any(s['metadata'] != base['metadata'] for s in snapshots):
        base_tables = set(base['tables'])
        changes = {}
        for snapshot in [source, target]:
            current_tables = set(snapshot['tables'])
            changed = [name for name in sorted(base_tables & current_tables)
                       if [c for c in snapshot['metadata'] if c['schema'] + '.' + c['table'] == name]
                       != [c for c in base['metadata'] if c['schema'] + '.' + c['table'] == name]]
            changes[snapshot['role']] = {'addedTables': sorted(current_tables - base_tables),
                                        'removedTables': sorted(base_tables - current_tables),
                                        'changedTables': changed}
        return {'status': 'THREE_WAY_SCHEMA_REVIEW_REQUIRED', 'schemaChanges': changes,
                'sourceSnapshotUtc': source['startedUtc'], 'targetSnapshotUtc': target['startedUtc'],
                'rowCounts': {s['role']: sum(len(rows) for rows in s['tables'].values()) for s in snapshots},
                'databaseChanged': False, 'incrementApplied': False, 'safeToBlindOverwrite': False,
                'note': 'Schema drift detected. No row classification or mutation; review migrations and new tables first.'}
    assert all(set(s['tables']) == set(base['tables']) for s in snapshots)
    tables = []
    for name in sorted(base['tables']):
        columns = [c for c in base['metadata'] if c['schema'] + '.' + c['table'] == name]
        rows = [s['tables'][name] for s in snapshots]
        record = {'table': name, 'baselineRows': len(rows[0]), 'sourceRows': len(rows[1]), 'targetRows': len(rows[2])}
        if not any(c['primary'] for c in columns):
            record.update(hasPrimaryKey=False, classification='manualMultisetReview',
                          allEqual=all(Counter(v for k, v in r) == Counter(v for k, v in rows[0]) for r in rows))
        else:
            assert all(len(dict(r)) == len(r) for r in rows), 'Duplicate primary-key digest'
            maps = [dict(r) for r in rows]
            keys = set().union(*(m.keys() for m in maps))
            counts = Counter(classify(*(m.get(k) for m in maps)) for k in keys)
            record.update(hasPrimaryKey=True, classifications=dict(sorted(counts.items())))
        tables.append(record)
    totals = Counter()
    for table in tables:
        totals.update(table.get('classifications', {}))
    return {'status': 'THREE_WAY_DIFFERENCES_CLASSIFIED', 'tableResults': tables,
            'totals': dict(sorted(totals.items())),
            'sourceSnapshotUtc': source['startedUtc'], 'targetSnapshotUtc': target['startedUtc'],
            'databaseChanged': False, 'incrementApplied': False, 'safeToBlindOverwrite': False,
            'note': 'Historical independent snapshots only. Source-only changes still require field policy, current hashes, references and external-store reconciliation. No deletion or update authorized by this classification alone.'}


def main():
    parser = argparse.ArgumentParser()
    for role in ['baseline', 'source', 'target']:
        parser.add_argument('--' + role, type=Path, default=ROOT / ('tmp/migration-' + role + '-row-digests-20261010.json'))
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/migration-three-way-audit-20261010.json')
    args = parser.parse_args()
    assert not args.output.exists(), 'Keep previous report; choose a new output path'
    snapshots = [json.loads(getattr(args, role).read_text()) for role in ['baseline', 'source', 'target']]
    result = compare(*snapshots)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'tableResults'}, indent=2))


if __name__ == '__main__':
    main()
