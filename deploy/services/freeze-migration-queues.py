"""Freeze only restored target queues, preserving original values for reconciliation."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path('/data/singux-migration-20261009')
SCHEDULE = "status IN ('CREATE','EXECUTING','CONTINUE','FAIL')"
RETRY = 'status IN (1,3)'


def sql(query):
    command = ('exec mysql --user=root --password="$MYSQL_ROOT_PASSWORD" '
               '--batch --skip-column-names agent_platform -e ' + shlex.quote(query))
    result = subprocess.run(['docker', 'exec', 'singux-mysql-1', 'sh', '-c', command],
                            capture_output=True, text=True)
    assert result.returncode == 0, 'Target queue SQL failed; inspect private database separately'
    return result.stdout.strip()


def main():
    os.umask(0o077)
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-mysql-1']))[0]
    label = container['Config']['Labels'].get('com.docker.compose.project.config_files')
    assert label == str(ROOT / 'compose.mysql.json'), 'Not the isolated migration MySQL'
    assert 'singux-backend-1' not in subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True).splitlines()
    assert json.loads((ROOT / 'mysql-restore-result.json').read_text())['status'] == 'MYSQL_RESTORED'
    original = ROOT / 'target-queue-original-locks.json'
    backup = ROOT / 'target-queues-before-freeze.sql.gz'
    assert not original.exists() and not backup.exists(), 'Preserve existing freeze backup'
    saved = {}
    for table, condition in [('schedule_task', SCHEDULE), ('pf_retry_data', RETRY)]:
        query = ("SELECT JSON_OBJECT('id',CAST(id AS CHAR),'status',status,'lockTime',lock_time) FROM "
                 + table + ' WHERE ' + condition)
        rows = sql(query)
        saved[table] = [json.loads(line) for line in rows.splitlines() if line]
    original.write_text(json.dumps(saved, indent=2))
    command = ('exec mysqldump --user=root --password="$MYSQL_ROOT_PASSWORD" '
               '--single-transaction --quick --no-tablespaces --set-gtid-purged=OFF '
               'agent_platform schedule_task pf_retry_data')
    # Popen performs the compression in this process; gzip.open cannot be passed as a subprocess fd.
    process = subprocess.Popen(['docker', 'exec', 'singux-mysql-1', 'sh', '-c', command],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    with gzip.open(backup, 'wb') as output:
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b''):
            output.write(chunk)
    assert process.wait() == 0, 'Queue backup failed; do not start backend'
    with backup.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    query = ("START TRANSACTION; UPDATE schedule_task SET lock_time='2099-01-01 00:00:00' WHERE "
             + SCHEDULE + "; UPDATE pf_retry_data SET lock_time='2099-01-01 00:00:00' WHERE "
             + RETRY + '; COMMIT;')
    sql(query)
    for table, condition in [('schedule_task', SCHEDULE), ('pf_retry_data', RETRY)]:
        remaining = sql('SELECT COUNT(*) FROM ' + table + ' WHERE ' + condition
                        + " AND (lock_time IS NULL OR lock_time<'2099-01-01 00:00:00')")
        assert remaining == '0', 'Queue freeze verification failed'
    record = {'status': 'TARGET_EXISTING_QUEUES_FROZEN',
              'scheduleRows': len(saved['schedule_task']), 'retryRows': len(saved['pf_retry_data']),
              'backupSha256': digest, 'sourceChanged': False, 'restoreAutomatically': False,
              'note': 'Reconcile with source before cutover; new target tasks are not globally disabled.'}
    (ROOT / 'queue-freeze-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
