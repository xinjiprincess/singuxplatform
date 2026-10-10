"""Inspect changed columns using hashes only; never apply reconciliation SQL."""
import argparse
from collections import Counter
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REMOTE = '/data/singux-migration-20261009/reconciliation-20261010'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_plan(source, target):
    assert source['status'] == target['status'] == 'ROW_DIGEST_SNAPSHOT_READY'
    assert source['role'] == 'source' and target['role'] == 'target'
    plan = {}
    for table in sorted(source['tables'].keys() & target['tables'].keys()):
        columns = [c for c in source['metadata'] if c['schema'] + '.' + c['table'] == table]
        other = [c for c in target['metadata'] if c['schema'] + '.' + c['table'] == table]
        assert columns == other, 'Schema drift requires separate review'
        if not any(c['primary'] for c in columns):
            continue
        a, b = dict(source['tables'][table]), dict(target['tables'][table])
        assert len(a) == len(source['tables'][table]) and len(b) == len(target['tables'][table])
        keys = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
        if keys:
            plan[table] = {'columns': columns, 'keys': keys}
    return plan


def compare_fields(source, target, source_snapshot, target_snapshot, plan):
    results = []
    for table, entry in plan.items():
        a, b = source['tables'][table], target['tables'][table]
        original_a, original_b = dict(source_snapshot['tables'][table]), dict(target_snapshot['tables'][table])
        names = [c['column'] for c in entry['columns']]
        fields = Counter()
        drift = missing = 0
        for key in entry['keys']:
            if key not in a or key not in b:
                missing += 1
                continue
            if a[key]['row'] != original_a[key] or b[key]['row'] != original_b[key]:
                drift += 1
            assert len(a[key]['fields']) == len(b[key]['fields']) == len(names)
            fields.update(name for name, x, y in zip(names, a[key]['fields'], b[key]['fields']) if x != y)
        results.append({'table': table, 'selectedRows': len(entry['keys']),
                        'missingSinceRowAudit': missing, 'changedSinceRowAudit': drift,
                        'differentColumns': dict(sorted(fields.items()))})
    return {'status': 'CHANGED_FIELDS_AUDITED', 'tables': results,
            'sourceSnapshotUtc': source['startedUtc'], 'targetSnapshotUtc': target['startedUtc'],
            'databaseChanged': False, 'incrementalApplied': False,
            'crossHostConsistentSnapshot': False,
            'note': 'Column names and difference counts only. Drift requires a fresh reconciliation snapshot; field differences alone do not authorize overwrites.'}


def remote_main():
    os.umask(0o077)
    dest = Path(REMOTE)
    assert dest.is_dir() and not dest.is_symlink()
    snapshot = json.loads((dest / 'row-digests.json').read_text())
    role = snapshot['role']
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-mysql-1']))[0]
    labels = container['Config']['Labels']
    assert labels['com.docker.compose.project'] == 'singux'
    if role == 'target':
        assert socket.gethostname() == 'vm133'
        assert labels['com.docker.compose.project.config_files'] == '/data/singux-migration-20261009/compose.mysql.json'
    else:
        assert role == 'source'
        assert labels['com.docker.compose.project.working_dir'] == '/home/singu-x-1.1.10-20260924-r1-linux-amd64'
    plan = json.loads((dest / 'field-plan.json').read_text())
    helper = load_module('digest', dest / 'audit-migration-row-digests.py')
    output = dest / 'field-digests.json'
    plan_sha = hashlib.sha256((dest / 'field-plan.json').read_bytes()).hexdigest()
    if output.exists():
        record = json.loads(output.read_text())
        assert record['planSha256'] == plan_sha and record['role'] == role
        print('ALREADY_AUDITED ' + role)
        return
    sql = ["SET time_zone='+00:00'; SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;",
           'START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;']
    for table, entry in plan.items():
        columns = entry['columns']
        assert columns == [c for c in snapshot['metadata'] if c['schema'] + '.' + c['table'] == table]
        assert all(re.fullmatch('[0-9a-f]{64}', key) for key in entry['keys'])
        schema, name = table.split('.')
        key_expr = helper.digest_expression([c['column'] for c in columns if c['primary']])
        row_expr = helper.digest_expression([c['column'] for c in columns])
        fields = ["IF(" + helper.quote(c['column']) + " IS NULL,'N',CONCAT('V',SHA2(CAST("
                  + helper.quote(c['column']) + ' AS BINARY),256)))' for c in columns]
        sql.append("SELECT '__TABLE__" + table + "';")
        sql.append('SELECT ' + ','.join([key_expr, row_expr] + fields) + ' FROM '
                   + helper.quote(schema) + '.' + helper.quote(name) + ' WHERE ' + key_expr
                   + ' IN (' + ','.join("'" + key + "'" for key in entry['keys']) + ');')
    sql.append('COMMIT;')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = helper.mysql('\n'.join(sql))
    tables, current = {}, None
    for line in raw.splitlines():
        if line.startswith('__TABLE__'):
            current = line[len('__TABLE__'):]
            tables[current] = {}
        else:
            key, row, *fields = line.split('\t')
            assert current and key in plan[current]['keys'] and key not in tables[current]
            assert re.fullmatch('[0-9a-f]{64}', row)
            assert all(value == 'N' or re.fullmatch('V[0-9a-f]{64}', value) for value in fields)
            tables[current][key] = {'row': row, 'fields': fields}
    assert tables.keys() == plan.keys()
    record = {'status': 'FIELD_DIGEST_SNAPSHOT_READY', 'role': role, 'startedUtc': started,
              'finishedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'planSha256': plan_sha, 'tables': tables, 'databaseChanged': False}
    partial = output.with_suffix('.json.part')
    partial.write_text(json.dumps(record, separators=(',', ':')))
    partial.replace(output)
    print(json.dumps({'role': role, 'status': record['status'],
                      'rows': sum(len(rows) for rows in tables.values())}))


def main():
    source = json.loads((ROOT / 'tmp/migration-source-row-digests-20261010.json').read_text())
    target = json.loads((ROOT / 'tmp/migration-target-row-digests-20261010.json').read_text())
    plan = make_plan(source, target)
    transport = load_module('transport', ROOT / 'deploy/services/stage-migration-images.py')
    password = os.environ.pop('SINGUX_SSH_PASSWORD')
    snapshots = []
    for host, role in [(transport.SOURCE, 'source'), (transport.TARGET, 'target')]:
        client = transport.t.paramiko.SSHClient()
        client.set_missing_host_key_policy(transport.Pinned())
        try:
            client.connect(host, username='root', password=password, look_for_keys=False,
                           allow_agent=False, timeout=20)
            client.get_transport().set_keepalive(15)
            transport.execute(client, 'test -d ' + REMOTE + ' && test ! -L ' + REMOTE)
            for name in ['audit-migration-field-differences.py', 'audit-migration-row-digests.py']:
                transport.write(client, REMOTE + '/' + name, (ROOT / 'deploy/services' / name).read_bytes())
            transport.write(client, REMOTE + '/field-plan.json', json.dumps(plan).encode())
            print(transport.execute(client, 'python3 ' + REMOTE + '/audit-migration-field-differences.py --remote', timeout=180), flush=True)
            with client.open_sftp() as ftp:
                with ftp.open(REMOTE + '/field-digests.json', 'rb') as handle:
                    data = handle.read()
            record = json.loads(data)
            assert record['role'] == role and record['status'] == 'FIELD_DIGEST_SNAPSHOT_READY'
            assert record['planSha256'] == hashlib.sha256(json.dumps(plan).encode()).hexdigest()
            (ROOT / ('tmp/migration-' + role + '-field-digests-20261010.json')).write_bytes(data)
            snapshots.append(record)
        finally:
            client.close()
    password = None
    result = compare_fields(*snapshots, source, target, plan)
    path = ROOT / 'outputs/migration-field-differences-20261010.json'
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote', action='store_true')
    args = parser.parse_args()
    remote_main() if args.remote else main()
