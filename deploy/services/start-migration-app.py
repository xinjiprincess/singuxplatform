"""Start target app with a separate HTTP test edge; backend stays isolated."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from importlib.machinery import SourceFileLoader

ROOT = Path('/data/singux-migration-20261009')


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    assert p.returncode == 0, 'Command failed: ' + ' '.join(args[:3])
    return p.stdout


def main():
    os.umask(0o077)
    assert json.loads((ROOT / 'runtime-start-result.json').read_text())['status'] == 'RUNTIME_READY'
    assert json.loads(run(['docker', 'network', 'inspect', 'singux_default']))[0]['Internal']
    queue = SourceFileLoader('queue_guard', str(ROOT / 'freeze-migration-queues.py')).load_module()
    for table, condition in [('schedule_task', queue.SCHEDULE), ('pf_retry_data', queue.RETRY)]:
        assert queue.sql('SELECT COUNT(*) FROM ' + table + ' WHERE ' + condition
                         + " AND (lock_time IS NULL OR lock_time<'2099-01-01')") == '0'
    path = ROOT / 'compose.app.test.json'
    if not path.exists():
        config = json.loads((ROOT / 'compose.app.private.json').read_text())
        config['networks']['test-edge'] = {'name': 'singux-test-edge'}
        config['services']['frontend']['networks']['test-edge'] = None
        config['services']['frontend']['ports'] = ['80:80', '8080:80']
        path.write_text(json.dumps(config, indent=2))
    cmd = ['docker', 'compose', '-p', 'singux', '-f', str(path)]
    run(cmd + ['config', '--quiet'])
    record_path = ROOT / 'app-start-result.json'
    record_path.write_text(json.dumps({'status': 'APP_STARTING', 'sourceChanged': False,
                                      'dnsChanged': False, 'testPort': 8080}, indent=2))
    run(cmd + ['up', '-d', '--pull', 'never'])
    checks = {}
    for _ in range(100):
        for name in ['backend', 'frontend', 'mcp-proxy']:
            obj = json.loads(run(['docker', 'inspect', 'singux-' + name + '-1']))[0]
            state = obj['State']
            checks[name] = state['Running'] and state.get('Health', {}).get('Status', 'healthy') == 'healthy'
        if all(checks.values()):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8080/login', timeout=5) as r:
                    checks['loginHtml'] = r.status == 200 and b'<html' in r.read().lower()
            except Exception:
                checks['loginHtml'] = False
            if checks.get('loginHtml'):
                break
        time.sleep(3)
    assert all(checks.values()), 'App readiness failed; inspect protected logs, preserve data'
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    record = {'status': 'APP_HTTP_READY', 'checks': checks, 'sourceChanged': False,
              'dnsChanged': False, 'testUrl': 'http://113.219.170.192:8080/login',
              'backendEgressBlocked': True, 'businessAcceptanceComplete': False,
              'laterSourceWritesIncluded': False}
    record_path.write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
