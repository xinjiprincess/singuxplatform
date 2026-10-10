"""Start verified target-only infrastructure; preserve MySQL and production."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
SERVICES = ['elasticsearch', 'etcd', 'minio', 'milvus', 'redis']


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    received = json.loads((ROOT / 'background-images-result.json').read_text())
    assert received['status'] == 'IMAGES_STAGED' and received['sha256'] == args.sha256
    expected = json.loads((ROOT / 'images.json').read_text())
    images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', *expected]))
    assert {name: obj['Id'] for name, obj in zip(expected, images)} == expected
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal']
    mysql = inspect('singux-mysql-1')
    assert mysql['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.mysql.json')
    assert mysql['State']['Health']['Status'] == 'healthy'
    assert json.loads((ROOT / 'queue-freeze-result.json').read_text())['status'] == 'TARGET_EXISTING_QUEUES_FROZEN'
    config_path = ROOT / 'compose.infra.json'
    config = json.loads(config_path.read_text())
    assert set(config['services']) == set(SERVICES)
    assert all(not service.get('ports') for service in config['services'].values())
    result_path = ROOT / 'infra-start-result.json'

    def save(status, checks=None):
        result = {'status': status, 'services': SERVICES, 'checks': checks or {},
                  'mysqlContainerUnchanged': inspect('singux-mysql-1')['Id'] == mysql['Id'],
                  'sourceChanged': False, 'platformStarted': False, 'imagesSha256': args.sha256}
        result_path.write_text(json.dumps(result, indent=2))

    save('INFRA_STARTING')
    subprocess.run(['docker', 'compose', '-p', 'singux', '-f', str(config_path),
                    'up', '-d', '--pull', 'never'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    checks = {}
    for _ in range(80):
        checks = {}
        for name in SERVICES:
            obj = inspect('singux-' + name + '-1')
            checks[name] = obj['State']['Running']
            if not checks[name]:
                continue
            try:
                if name == 'redis':
                    process = subprocess.run(['docker', 'exec', 'singux-redis-1', 'sh', '-c',
                                'exec redis-cli -a "$REDIS_PASSWORD" ping'], capture_output=True, timeout=10)
                    checks[name] = process.returncode == 0 and process.stdout.strip() == b'PONG'
                else:
                    ip = obj['NetworkSettings']['Networks']['singux_default']['IPAddress']
                    endpoint = {'elasticsearch': ':9200/_cluster/health', 'etcd': ':2379/health',
                                'minio': ':9000/minio/health/live', 'milvus': ':9091/healthz'}[name]
                    with opener.open('http://' + ip + endpoint, timeout=3) as response:
                        checks[name] = response.status == 200
                        if name == 'elasticsearch':
                            checks[name] = checks[name] and json.load(response)['status'] in {'yellow', 'green'}
                        elif name == 'etcd':
                            checks[name] = checks[name] and json.load(response).get('health') in {True, 'true'}
            except Exception:
                checks[name] = False
        if all(checks.values()):
            break
        time.sleep(3)
    assert inspect('singux-mysql-1')['Id'] == mysql['Id'], 'MySQL unexpectedly replaced'
    save('INFRA_READY' if all(checks.values()) else 'INFRA_NOT_READY', checks)
    assert all(checks.values()), 'Target infrastructure not ready; inspect target private logs'
    print(json.dumps({'status': 'INFRA_READY', 'checks': checks, 'mysqlContainerUnchanged': True}), flush=True)


if __name__ == '__main__':
    main()
