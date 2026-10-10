"""Restore the immutable migration dump into a networkless disposable audit DB.

Never connects to or restores the application's live MySQL. Leaves the stopped
audit container and its separate volume for review; no volumes are removed.
"""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

ROOT = Path('/data/singux-migration-20261009')
DEST = ROOT / 'reconciliation-20261010' / 'baseline'
NAME = 'singux-migration-baseline-audit-20261010'
IMAGE = 'sha256:81f6c182a6bec2ca54bf98a9a6255e0c62e7df504afb9cb1c621c38a9f35da92'
LABEL = 'singux.migration.audit-baseline'


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs)


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]).stdout)[0]


def query(sql):
    return run(['docker', 'exec', '-i', NAME, 'mysql', '--protocol=socket',
                '--user=root', '--batch', '--skip-column-names', '--raw',
                '--default-character-set=utf8mb4'], input=sql.encode(), timeout=600).stdout.decode()


def main():
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    assert ROOT.is_dir() and not ROOT.is_symlink()
    live = inspect('singux-mysql-1')
    assert live['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.mysql.json')
    assert live['Image'] == IMAGE
    expected = json.loads((ROOT / 'mysql-export.json').read_text())['sha256']
    dump = ROOT / 'application-databases.sql.gz'
    assert hashlib.sha256(dump.read_bytes()).hexdigest() == expected
    output = DEST / 'row-digests.json'
    if output.exists():
        result = json.loads((DEST / 'result.json').read_text())
        assert result['status'] == 'BASELINE_DIGEST_VERIFIED'
        assert result['snapshotSha256'] == expected
        assert result['digestSha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
        print('BASELINE_ALREADY_VERIFIED'); return
    assert not DEST.exists(), 'Incomplete audit exists; review instead of repeating restore'
    assert shutil.disk_usage(ROOT).free > 8 * 1024**3
    assert not run(['docker', 'ps', '-aq', '--filter', 'name=^/' + NAME + '$']).stdout.strip()
    assert not run(['docker', 'volume', 'ls', '-q', '--filter', 'name=^' + NAME + '$']).stdout.strip()
    DEST.mkdir(mode=0o700)
    before = run(['docker', 'ps', '-q', '--no-trunc']).stdout.splitlines()
    run(['docker', 'volume', 'create', '--label', LABEL + '=' + expected, NAME])
    run(['docker', 'run', '-d', '--name', NAME, '--label', LABEL + '=' + expected,
         '--network', 'none', '--memory', '768m', '--memory-swap', '1g', '--cpus', '0.5',
         '--pids-limit', '256', '--restart', 'no', '--mount',
         'type=volume,source=' + NAME + ',target=/var/lib/mysql',
         '-e', 'MYSQL_ALLOW_EMPTY_PASSWORD=yes', IMAGE,
         '--skip-networking', '--event-scheduler=OFF', '--innodb-buffer-pool-size=128M',
         '--performance-schema=OFF'])
    try:
        audit = inspect(NAME)
        assert audit['HostConfig']['NetworkMode'] == 'none'
        assert not audit['HostConfig'].get('PortBindings')
        assert audit['Mounts'][0]['Name'] == NAME
        for _ in range(180):
            try:
                logs = run(['docker', 'logs', NAME]).stdout
                if b'MySQL init process done. Ready for start up.' in logs and query('SELECT 1;').strip() == '1':
                    break
            except subprocess.CalledProcessError:
                pass
            time.sleep(2)
        else:
            raise RuntimeError('Audit-only MySQL startup timed out')
        with gzip.open(dump, 'rb') as source:
            process = subprocess.Popen(['docker', 'exec', '-i', NAME, 'mysql',
                                        '--protocol=socket', '--user=root'],
                                       stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                shutil.copyfileobj(source, process.stdin)
                process.stdin.close()
                assert process.wait(timeout=600) == 0, 'Baseline-only import failed; no live data changed'
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=30)
        assert query("SELECT @@event_scheduler;").strip() == 'OFF'
        spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('audit-migration-row-digests.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.snapshot('baseline', output, query)
    finally:
        run(['docker', 'stop', '--time', '30', NAME], timeout=60)
    assert inspect('singux-mysql-1')['Id'] == live['Id']
    after = run(['docker', 'ps', '-q', '--no-trunc']).stdout.splitlines()
    assert sorted(before) == sorted(after), 'Running application container set changed during audit'
    result = {'status': 'BASELINE_DIGEST_VERIFIED', 'snapshotSha256': expected,
              'digestSha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'liveDatabaseChanged': False, 'sourceChanged': False,
              'auditContainerStopped': True, 'auditNetwork': 'none', 'incrementApplied': False}
    (DEST / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
