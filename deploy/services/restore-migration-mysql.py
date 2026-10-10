"""Prioritize a pinned MySQL image and restore the staged logical snapshot on the empty target."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('migration', ROOT / 'deploy/services/stage-migration-images.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    password = os.environ.pop('SINGUX_SSH_PASSWORD')
    clients = []
    try:
        for host in (m.SOURCE, m.TARGET):
            c = m.t.paramiko.SSHClient()
            c.set_missing_host_key_policy(m.Pinned())
            c.connect(host, username='root', password=password, look_for_keys=False, allow_agent=False, timeout=20)
            c.get_transport().set_keepalive(20)
            clients.append(c)
        password = None
        old, new = clients
        assert not m.execute(new, 'docker ps -aq'), 'Refuse nonempty target'
        assert not m.execute(new, 'docker volume ls -q'), 'Refuse existing target volumes'
        expected = json.loads(m.execute(old, 'docker image inspect mysql:8.4'))[0]['Id']
        expected_dump = json.loads(m.execute(new, 'cat ' + m.REMOTE + '/mysql-export.json'))['sha256']
        actual_dump = m.execute(new, 'sha256sum ' + m.REMOTE + '/application-databases.sql.gz').split()[0]
        assert expected_dump == actual_dump
        base = '/home/singu-x-1.1.10-20260924-r1-linux-amd64'
        command = ['docker', 'compose', '-p', 'singux', '--env-file', base + '/.env']
        for name in ['compose.json', 'compose.mcp.json', 'compose.runtime.json', 'compose.filing.json']:
            command += ['-f', base + '/' + name]
        config = json.loads(m.execute(old, shlex.join(command + ['config', '--format', 'json'])))
        service = config['services']['mysql']
        service['image'] = 'mysql:8.4'
        service['ports'] = []
        # The dump supplies the schema; never initialize an administrator from old SQL seed files.
        service['volumes'] = [v for v in service['volumes'] if v['type'] == 'volume']
        assert len(service['volumes']) == 1
        volume = service['volumes'][0]['source']
        minimal = {'name': 'singux', 'services': {'mysql': service},
                   'volumes': {volume: config['volumes'][volume]}}
        minimal['services']['mysql'].pop('networks', None)
        minimal['networks'] = {'default': {'name': 'singux_default', 'internal': True}}
        path = m.REMOTE + '/compose.mysql.json'
        m.write(new, path, json.dumps(minimal, indent=2))
        print('MYSQL_IMAGE_TRANSFER_START', flush=True)
        _, source, errors = old.exec_command("bash -o pipefail -c 'docker save mysql:8.4 | nice -n 10 gzip -1'", timeout=3600)
        stdin, output, load_errors = new.exec_command('docker load', timeout=3600)
        transferred = 0
        last = time.monotonic()
        while chunk := source.read(256 * 1024):
            stdin.write(chunk)
            transferred += len(chunk)
            if time.monotonic() - last > 20:
                print('MYSQL_IMAGE_BYTES=' + str(transferred), flush=True)
                last = time.monotonic()
        stdin.flush()
        stdin.channel.shutdown_write()
        source_error = errors.read().decode()
        assert source.channel.recv_exit_status() == 0, 'Source image export failed: ' + source_error[-300:]
        output.read()
        load_error = load_errors.read().decode()
        assert output.channel.recv_exit_status() == 0, 'Image import failed: ' + load_error[-300:]
        actual = json.loads(m.execute(new, 'docker image inspect mysql:8.4'))[0]['Id']
        assert actual == expected, 'MySQL image ID mismatch'
        compose = 'docker compose -p singux -f ' + shlex.quote(path)
        print(m.execute(new, compose + ' up -d --no-deps --pull never mysql'), flush=True)
        for _ in range(120):
            state = json.loads(m.execute(new, 'docker inspect singux-mysql-1'))[0]['State']
            if state.get('Health', {}).get('Status') == 'healthy':
                break
            if not state['Running']:
                raise RuntimeError('Target MySQL stopped')
            time.sleep(3)
        else:
            raise RuntimeError('Target MySQL readiness timed out')
        restore = ('set -o pipefail; gzip -dc ' + m.REMOTE + '/application-databases.sql.gz | '
                   'docker exec -i singux-mysql-1 sh -c ' + shlex.quote('exec mysql --user=root --password="$MYSQL_ROOT_PASSWORD"'))
        m.execute(new, 'bash -c ' + shlex.quote(restore), timeout=600)
        query = 'exec mysql --user=root --password="$MYSQL_ROOT_PASSWORD" --batch --skip-column-names -e "SELECT table_schema,COUNT(*) FROM information_schema.tables WHERE table_schema IN (\'agent_platform\',\'agent_custom_table\') GROUP BY table_schema"'
        counts = m.execute(new, 'docker exec singux-mysql-1 sh -c ' + shlex.quote(query))
        assert 'agent_platform' in counts
        record = {'status': 'MYSQL_RESTORED', 'target': m.TARGET, 'imageId': actual,
                  'snapshotSha256': actual_dump, 'schemaTableCounts': counts,
                  'sourceServicesStopped': False, 'targetPlatformStarted': False,
                  'laterSourceWritesIncluded': False}
        m.write(new, m.REMOTE + '/mysql-restore-result.json', json.dumps(record, indent=2))
        (ROOT / 'outputs/migration-mysql-restored-20261010.json').write_text(json.dumps(record, indent=2))
        print(json.dumps(record), flush=True)
    finally:
        for c in clients:
            c.close()


if __name__ == '__main__':
    main()
