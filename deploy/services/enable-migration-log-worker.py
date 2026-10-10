"""Resume only internal log indexing; keep all other restored queues frozen."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT = Path('/data/singux-migration-20261009')


def main():
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    backend = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
    assert backend['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.app.test.json')
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    assert json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]['Internal']
    spec = importlib.util.spec_from_file_location('queue', ROOT / 'freeze-migration-queues.py')
    queue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(queue)
    predicate = "bean_id='logApplicationService' AND task_id='logApplicationService'"
    assert queue.sql('SELECT COUNT(*) FROM schedule_task WHERE ' + predicate) == '1'
    for table, condition in [('schedule_task', queue.SCHEDULE + ' AND NOT (' + predicate + ')'), ('pf_retry_data', queue.RETRY)]:
        assert queue.sql('SELECT COUNT(*) FROM ' + table + ' WHERE ' + condition
                         + " AND (lock_time IS NULL OR lock_time<'2099-01-01')") == '0'
    result_path = ROOT / 'log-worker-result.json'
    if result_path.exists():
        result = json.loads(result_path.read_text())
        assert result['status'] == 'INTERNAL_LOG_WORKER_ENABLED'
        print(json.dumps(result))
        return
    before = ROOT / 'log-worker-before.json'
    assert not before.exists(), 'Review existing worker backup before retry'
    raw = queue.sql("SELECT JSON_OBJECT('id',CAST(id AS CHAR),'status',status,'lockTime',lock_time) FROM schedule_task WHERE " + predicate)
    row = json.loads(raw)
    assert row['status'] == 'CONTINUE' and row['lockTime'].startswith('2099-01-01')
    before.write_text(json.dumps(row, indent=2))
    count = queue.sql("START TRANSACTION; UPDATE schedule_task SET lock_time=NOW(6) WHERE "
                      + predicate + " AND status='CONTINUE' AND lock_time='2099-01-01 00:00:00'; SELECT ROW_COUNT(); COMMIT;")
    assert count == '1', 'Worker changed concurrently; review before retry'
    result = {'status': 'INTERNAL_LOG_WORKER_ENABLED', 'worker': 'logApplicationService',
              'otherRestoredQueuesFrozen': True, 'backendEgressBlocked': True,
              'sourceChanged': False, 'outboundNotificationsEnabled': False,
              'note': 'Only Redis log queue to internal Elasticsearch. Billing, notifications and other restored tasks remain frozen.'}
    result_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
