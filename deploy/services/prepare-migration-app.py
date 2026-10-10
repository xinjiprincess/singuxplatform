"""Prepare private application services against restored target volumes."""
import copy
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/data/singux-migration-20261009')
CONFIGS = ROOT / 'business-staged/business-export/configs'
SERVICES = ['backend', 'frontend', 'mcp-proxy']


def build(source, configs):
    result = {'name': 'singux', 'services': {},
              'networks': {'default': {'external': True, 'name': 'singux_default'}},
              'volumes': {'backend-uploads': {'external': True, 'name': 'singux_backend-uploads'}}}
    for name in SERVICES:
        service = copy.deepcopy(source['services'][name])
        service.pop('depends_on', None)
        service['ports'] = []
        assert set(service.get('networks', {})) == {'default'}
        for mount in service.get('volumes', []):
            if mount['type'] == 'bind':
                assert name == 'frontend' and mount.get('read_only')
                assert mount['target'] == '/etc/nginx/templates/default.conf.template'
                original = Path(mount['source'])
                assert original.is_absolute() and '..' not in original.parts
                mapped = configs / str(original).lstrip('/')
                assert mapped.is_file() and not mapped.is_symlink()
                mount['source'] = str(mapped)
                mount['bind'] = {'create_host_path': False}
            else:
                assert mount['type'] == 'volume' and name == 'backend'
                assert mount['source'] == 'backend-uploads' and mount['target'] == '/data/uploads'
        result['services'][name] = service
    return result


def main():
    os.umask(0o077)
    required = {'infra-start-result.json': 'INFRA_READY',
                'uploads-restore-result.json': 'UPLOADS_VOLUME_RESTORED',
                'minio-restore-result.json': 'MINIO_EXPORTED_OBJECTS_RESTORED',
                'elasticsearch-restore-result.json': 'ELASTICSEARCH_DOCUMENTS_RESTORED',
                'vector-restore-result.json': 'VISIBLE_VECTORS_RESTORED',
                'queue-freeze-result.json': 'TARGET_EXISTING_QUEUES_FROZEN'}
    for name, status in required.items():
        assert json.loads((ROOT / name).read_text())['status'] == status
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal']
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True).splitlines()
    assert not any('singux-' + name + '-1' in names for name in SERVICES)
    source = json.loads((CONFIGS / 'platform-resolved.json').read_text())
    config = build(source, CONFIGS)
    path = ROOT / 'compose.app.private.json'
    assert not path.exists(), 'Refuse replacing existing configuration'
    path.write_text(json.dumps(config, indent=2))
    subprocess.run(['docker', 'compose', '-p', 'singux', '-f', str(path), 'config', '--quiet'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    record = {'status': 'PRIVATE_APP_CONFIG_PREPARED', 'services': SERVICES,
              'started': False, 'publicPorts': [], 'sourceChanged': False,
              'runtimeConnected': False, 'queueFreezeNotGlobalSchedulerDisable': True,
              'pending': ['runtime configuration and private aliases', 'standby background-job audit',
                          'host.docker.internal dependencies', 'business validation', 'source incremental reconciliation']}
    (ROOT / 'app-preparation-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
