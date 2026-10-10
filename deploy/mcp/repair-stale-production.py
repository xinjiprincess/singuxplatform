"""Repair orphaned historical deployment indicators, never mark untested services ready."""
import json
import os
from pathlib import Path
import subprocess


def sql(query):
    p = subprocess.run(['docker', 'exec', '-i', 'singux-mysql-1', 'sh', '-c',
        'exec mysql --default-character-set=utf8mb4 -uroot --password="$MYSQL_ROOT_PASSWORD" -B -N --raw'],
        input=query, capture_output=True, text=True)
    assert p.returncode == 0, 'MCP state repair query rejected'
    return p.stdout


def main():
    os.umask(0o077)
    root = Path('/data/singux-mcp-state-repair-20261010')
    assert not root.exists(), 'Preserve previous repair backup'
    schema = sql("SELECT TABLE_SCHEMA FROM information_schema.tables WHERE TABLE_NAME='mcp_config'").strip()
    assert schema.replace('_', '').isalnum()
    table = schema + '.mcp_config'
    tasks = schema + '.schedule_task'
    condition = ("m.deploy_status='Deploying' AND m.modified < NOW() - INTERVAL 1 HOUR AND NOT EXISTS "
        "(SELECT 1 FROM " + tasks + " t WHERE t.bean_id='mcpDeployTaskService' "
        "AND JSON_UNQUOTE(JSON_EXTRACT(t.params,'$.id'))=CAST(m.id AS CHAR) "
        "AND t.status IN ('CONTINUE','EXECUTING'))")
    raw = sql("SELECT JSON_OBJECT('id',m.id,'status',m.deploy_status,'modified',m.modified) FROM "
              + table + ' m WHERE ' + condition)
    before = [json.loads(line) for line in raw.splitlines()]
    root.mkdir(mode=0o700)
    (root / 'before.json').write_text(json.dumps(before, indent=2))
    ids = [int(row['id']) for row in before]
    if ids:
        sql('START TRANSACTION; UPDATE ' + table + " m SET m.deploy_status='DeployFailed' WHERE "
            + condition + ' AND m.id IN (' + ','.join(map(str, ids)) + '); COMMIT;')
    states = sql('SELECT id,deploy_status FROM ' + table + ' WHERE id IN ('
                 + ','.join(map(str, ids or [-1])) + ')')
    assert all(line.split('\t')[1] == 'DeployFailed' for line in states.splitlines())
    result = {'status': 'MCP_ORPHANED_STATES_REPAIRED', 'ids': ids, 'count': len(ids),
              'configsChanged': False, 'markedReadyWithoutTest': False,
              'activeTasksChanged': False, 'note': 'Historical orphaned deployments now allow explicit retry.'}
    (root / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
