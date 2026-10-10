"""Read-only production preflight for the reviewed MCP recovery release."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

DEPLOY = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
BASE_JAR = 'de8f680b7fe3d89f8b7cc661d396036172dc0d8a82ff0091004cb256cc2d2598'

def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Preflight command failed: ' + ' '.join(args[:3]))
    return result.stdout.decode().strip()

compose = ['docker', 'compose', '-p', 'singux', '--project-directory', str(DEPLOY),
           '--env-file', str(DEPLOY / '.env'), '-f', str(DEPLOY / 'compose.json')]
run(compose + ['config', '--quiet'])
items = json.loads(run(['docker', 'inspect'] + run(compose + ['ps', '-q']).split()))
services = {}
volumes = set()
for item in items:
    labels = item['Config'].get('Labels') or {}
    service = labels.get('com.docker.compose.service')
    if labels.get('com.docker.compose.project') != 'singux' or item['State']['Status'] != 'running':
        raise RuntimeError('Unexpected project or container state')
    if labels.get('com.docker.compose.project.working_dir') != str(DEPLOY):
        raise RuntimeError('Unexpected deployment directory')
    if service in services:
        raise RuntimeError('Duplicate service')
    services[service] = item
    for mount in item['Mounts']:
        if mount['Type'] == 'volume': volumes.add(mount['Name'])
        elif mount.get('RW'): raise RuntimeError('Writable bind mount requires separate review')
        if service == 'backend' and mount['Destination'].startswith('/app'):
            raise RuntimeError('Mounted application code cannot be replaced safely')
required = {'backend', 'frontend', 'mysql', 'redis', 'elasticsearch', 'minio', 'milvus', 'etcd'}
if set(services) != required:
    raise RuntimeError('Production service set changed; review before deployment')
for name in ('backend', 'frontend', 'mysql'):
    if services[name]['State'].get('Health', {}).get('Status') != 'healthy':
        raise RuntimeError('Existing service is not healthy: ' + name)
if not os.path.ismount('/data'): raise RuntimeError('Data disk is not mounted')
backend = services['backend']
actual = run(['docker', 'exec', backend['Id'], 'sha256sum', '/app/app.jar']).split()[0]
if actual != BASE_JAR: raise RuntimeError('Production JAR changed; recovery baseline does not match')
config = json.loads(run(compose + ['config', '--format', 'json']))
if 'default' not in config['services']['backend'].get('networks', {}):
    raise RuntimeError('Backend does not use default network; review MCP network mapping')
volume_info = json.loads(run(['docker', 'volume', 'inspect'] + sorted(volumes)))
sizes = {v['Name']: int(run(['du', '-sk', v['Mountpoint']]).split()[0]) * 1024 for v in volume_info}
free = shutil.disk_usage('/data').free
needed = sum(sizes.values()) * 2 + 12 * 1024 ** 3
if free < needed: raise RuntimeError('Insufficient backup/import space on data disk')
print(json.dumps({'check': 'OK', 'deployment': str(DEPLOY), 'backendJarSha256': actual,
    'images': {name: item['Config']['Image'] for name, item in services.items()},
    'volumeCount': len(volumes), 'volumeBytes': sum(sizes.values()),
    'dataFreeBytes': free, 'requiredBytes': needed,
    'mcpConfigured': bool(config['services']['backend'].get('environment', {}).get('MCP_PROXY_URL'))}, indent=2))
