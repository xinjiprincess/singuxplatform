"""Replace only the target frontend host port 80 with 8000, retaining 8080."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
CONFIG = ROOT / 'compose.app.test.json'
BACKUP = ROOT / 'http-port-8000-20261011'


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def containers():
    return {c['Name']: c for c in json.loads(run('docker', 'inspect', *run('docker', 'ps', '-q').split()))}


def main():
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    BACKUP.mkdir(mode=0o700, exist_ok=True)
    output = BACKUP / 'result.json'
    if output.exists():
        result = json.loads(output.read_text())
        assert result['status'] == 'TARGET_HTTP_PORT_CHANGED'
        print(json.dumps(result)); return
    before = containers()
    frontend = before['/singux-frontend-1']
    assert frontend['Config']['Labels']['com.docker.compose.project.config_files'] == str(CONFIG)
    original = CONFIG.read_bytes()
    config = json.loads(original)
    assert config['services']['frontend']['ports'] == ['80:80', '8080:80']
    assert set(frontend['NetworkSettings']['Networks']) == {'singux_default', 'singux-test-edge'}
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', 8000))
    (BACKUP / 'compose.before.json').write_bytes(original)
    command = ['docker', 'compose', '-p', 'singux', '-f', str(CONFIG)]
    try:
        config['services']['frontend']['ports'] = ['8000:80', '8080:80']
        CONFIG.write_text(json.dumps(config, indent=2))
        run(*command, 'config', '-q')
        run(*command, 'up', '-d', '--no-deps', '--pull', 'never', 'frontend')
        for _ in range(45):
            current = json.loads(run('docker', 'inspect', 'singux-frontend-1'))[0]
            if current['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(2)
        else:
            raise RuntimeError('Frontend health check failed')
        assert current['Image'] == frontend['Image'] and current['Mounts'] == frontend['Mounts']
        assert set(current['NetworkSettings']['Networks']) == set(frontend['NetworkSettings']['Networks'])
        ports = current['HostConfig']['PortBindings']['80/tcp']
        assert {p['HostPort'] for p in ports} == {'8000', '8080'}
        after = containers()
        for name, item in before.items():
            if name != '/singux-frontend-1':
                assert after[name]['Id'] == item['Id'], 'Unexpected service recreation'
        for port in [8000, 8080]:
            with urllib.request.urlopen('http://127.0.0.1:' + str(port) + '/login', timeout=20) as response:
                assert response.status == 200 and b'<html' in response.read().lower()
        result = {'status': 'TARGET_HTTP_PORT_CHANGED', 'hostPorts': [8000, 8080],
                  'containerPort': 80, 'imageUnchanged': True, 'otherContainersUnchanged': True,
                  'databaseChanged': False, 'sourceChanged': False, 'publicVerified': False,
                  'backup': str(BACKUP)}
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    except BaseException:
        CONFIG.write_bytes(original)
        run(*command, 'up', '-d', '--no-deps', '--pull', 'never', 'frontend')
        raise


if __name__ == '__main__':
    main()
