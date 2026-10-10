"""Private, read-only InnoDB row fingerprints for incremental reconciliation."""
from collections import defaultdict
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import socket
import subprocess

ROOT = Path('/data/singux-migration-20261009')
DEST = ROOT / 'reconciliation-20261010'


def mysql(query):
    result = subprocess.run(['docker', 'exec', '-i', 'singux-mysql-1', 'sh', '-c',
        'exec mysql --default-character-set=utf8mb4 --user=root --password="$MYSQL_ROOT_PASSWORD" --batch --skip-column-names --raw'],
        input=query, text=True, capture_output=True, timeout=600)
    assert result.returncode == 0, 'Read-only digest query rejected; no database changes made'
    return result.stdout


def quote(name):
    return '`' + name.replace('`', '``') + '`'


def digest_expression(columns):
    pieces = ["IF(" + quote(name) + " IS NULL,'N',CONCAT('V',SHA2(CAST(" + quote(name)
              + ' AS BINARY),256)))' for name in columns]
    return "SHA2(CONCAT_WS(''," + ','.join(pieces) + '),256)'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', help='New immutable snapshot subdirectory; existing snapshots are never replaced')
    args = parser.parse_args()
    if args.run_id:
        assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.run_id), 'Invalid run identifier'
    os.umask(0o077)
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-mysql-1']))[0]
    assert container['Config']['Labels']['com.docker.compose.project'] == 'singux'
    assert ROOT.is_dir() and not ROOT.is_symlink()
    if socket.gethostname() == 'vm133':
        assert container['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.mysql.json')
        role = 'target'
    else:
        assert container['Config']['Labels']['com.docker.compose.project.working_dir'] == '/home/singu-x-1.1.10-20260924-r1-linux-amd64'
        role = 'source'
    DEST.mkdir(mode=0o700, exist_ok=True)
    destination = DEST / args.run_id if args.run_id else DEST
    assert not destination.is_symlink()
    destination.mkdir(mode=0o700, exist_ok=True)
    output = destination / 'row-digests.json'
    if output.exists():
        assert json.loads(output.read_text())['status'] == 'ROW_DIGEST_SNAPSHOT_READY'
        print('ALREADY_AUDITED ' + role); return
    snapshot(role, output, mysql)


def snapshot(role, output, query):
    """Fingerprint an explicitly supplied, already validated database connection."""
    metadata_query = """SELECT JSON_OBJECT('schema',c.TABLE_SCHEMA,'table',c.TABLE_NAME,
        'column',c.COLUMN_NAME,'position',c.ORDINAL_POSITION,'type',c.COLUMN_TYPE,
        'primary',c.COLUMN_KEY='PRI','engine',t.ENGINE)
        FROM information_schema.COLUMNS c JOIN information_schema.TABLES t
        ON c.TABLE_SCHEMA=t.TABLE_SCHEMA AND c.TABLE_NAME=t.TABLE_NAME
        WHERE c.TABLE_SCHEMA IN ('agent_platform','agent_custom_table') AND t.TABLE_TYPE='BASE TABLE'
        ORDER BY c.TABLE_SCHEMA,c.TABLE_NAME,c.ORDINAL_POSITION;"""
    metadata = [json.loads(line) for line in query(metadata_query).splitlines()]
    assert metadata, 'Missing application schemas'
    tables = defaultdict(list)
    for column in metadata:
        tables[(column['schema'], column['table'])].append(column)
    statements = ["SET time_zone='+00:00'; SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;",
                  'START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;']
    for (schema, table), columns in tables.items():
        marker = schema + '.' + table
        assert all(char.isalnum() or char in '_.' for char in marker)
        statements.append("SELECT '__TABLE__" + marker + "';")
        row_hash = digest_expression([column['column'] for column in columns])
        primary = [column['column'] for column in columns if column['primary']]
        key_hash = digest_expression(primary) if primary else row_hash
        statements.append('SELECT ' + key_hash + ',' + row_hash + ' FROM ' + quote(schema) + '.' + quote(table) + ';')
    statements.append('COMMIT;')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = query('\n'.join(statements))
    manifests = {}
    current = None
    for line in raw.splitlines():
        if line.startswith('__TABLE__'):
            current = line[len('__TABLE__'):]
            manifests[current] = []
        else:
            key, value = line.split('\t')
            assert current and len(key) == len(value) == 64
            assert all(char in '0123456789abcdef' for char in key + value)
            manifests[current].append([key, value])
    assert len(manifests) == len(tables)
    for rows in manifests.values(): rows.sort()
    record = {'status': 'ROW_DIGEST_SNAPSHOT_READY', 'role': role, 'startedUtc': started,
              'finishedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'metadata': metadata, 'tables': manifests,
              'writesPaused': False, 'sourceChanged': False, 'databaseChanged': False,
              'crossHostConsistentSnapshot': False, 'crossStoreConsistentSnapshot': False,
              'nonTransactionalTables': ['.'.join(key) for key, cols in tables.items() if cols[0]['engine'] != 'InnoDB']}
    partial = output.with_suffix('.json.part')
    partial.write_text(json.dumps(record, separators=(',', ':')))
    partial.replace(output)
    summary = {key: record[key] for key in ['status', 'role', 'startedUtc', 'finishedUtc', 'databaseChanged', 'nonTransactionalTables']}
    summary.update(tables=len(manifests), rows=sum(map(len, manifests.values())),
                   sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    output.with_name('digest-summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
