"""Prepare Linux configuration separately from the local reference deployment."""
import json
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent


def main():
    config = yaml.safe_load((HERE / 'rcoder.yml').read_text())
    config['cleanup_config'].update(idle_timeout_seconds=600, container_protection_seconds=120)
    docker = config['docker_config']
    docker.update(network_mode='singux-execution', network_base_name='singux-runtime', container_ttl_seconds=600)
    for service in docker['multi_image_config']['services'].values():
        service['network_mode'] = 'singux-execution'
        service['security'] = {'privileged': False, 'cap_drop': ['NET_RAW', 'NET_ADMIN'],
                               'security_opt': ['no-new-privileges:true'], 'pids_limit': 256, 'init': True}
        service['resource_limits']['swap_limit'] = service['resource_limits']['memory_limit'] * 2
    (HERE / 'rcoder.production.json').write_text(json.dumps(config, indent=2))
    gateway = (HERE / 'gateway.conf').read_text()
    # Production has no direct test-project preview listener.
    start = gateway.index('  server {\n    listen 4000;')
    end = gateway.index('  server {\n    listen 60000;', start)
    gateway = gateway[:start] + gateway[end:]
    (HERE / 'gateway.production.conf').write_text(gateway)
    print('PRODUCTION_CONFIG_PREPARED')


if __name__ == '__main__':
    main()
