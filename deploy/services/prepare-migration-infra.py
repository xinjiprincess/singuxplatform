"""Generate target infrastructure Compose without touching existing MySQL."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/data/singux-migration-20261009')
SERVICES = ['elasticsearch', 'etcd', 'minio', 'milvus', 'redis']


def build(source):
    config = {'name': 'singux', 'services': {}, 'volumes': {},
              'networks': {'default': {'external': True, 'name': 'singux_default'}}}
    for name in SERVICES:
        service = dict(source['services'][name])
        service['ports'] = []
        assert all(mount['type'] == 'volume' for mount in service.get('volumes', []))
        assert all(dependency in SERVICES for dependency in service.get('depends_on', {}))
        config['services'][name] = service
        for mount in service.get('volumes', []):
            volume = mount['source']
            config['volumes'][volume] = source['volumes'][volume]
    return config


def main():
    os.umask(0o077)
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal'], 'Preserve isolated network'
    source = json.loads((ROOT / 'business-staged/business-export/configs/platform-resolved.json').read_text())
    config = build(source)
    path = ROOT / 'compose.infra.json'
    assert not path.exists(), 'Refuse replacing an existing deployment configuration'
    path.write_text(json.dumps(config, indent=2))
    subprocess.run(['docker', 'compose', '-p', 'singux', '-f', str(path), 'config', '--quiet'], check=True)
    record = {'status': 'INFRA_CONFIG_PREPARED', 'services': SERVICES,
              'started': False, 'mysqlChanged': False, 'publicPorts': []}
    (ROOT / 'infra-preparation-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
