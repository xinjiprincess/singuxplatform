"""Add private Linux runtime services without replacing the existing platform containers."""
import datetime
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
WORK = Path('/data/singux-services/workspace')
PROJECT = 'singux-runtime'


def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:3]))
    return result.stdout.decode().strip()


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Root required')
    os.umask(0o077)
    before = json.loads(run(['docker', 'inspect', *run(['docker', 'ps', '-q']).split()]))
    platform = {c['Name']: (c['Id'], c['Image']) for c in before}
    if any(name.startswith('/singux-runtime-') for name in platform):
        raise RuntimeError('Runtime containers already exist; review required')
    if WORK.exists() and any(WORK.iterdir()):
        raise RuntimeError('Workspace is not empty; do not change existing ownership')
    if not any(c['Name'] == '/singux-backend-1' and c['State'].get('Health', {}).get('Status') == 'healthy' for c in before):
        raise RuntimeError('Existing backend must be healthy')
    if run(['findmnt', '-n', '-o', 'TARGET', '-T', '/data']) != '/data':
        raise RuntimeError('Data disk missing')
    if shutil.disk_usage('/data').free < 25 * 1024**3:
        raise RuntimeError('Need 25 GiB free for image import and runtime')
    config_path = HERE / 'compose.runtime.json'
    if config_path.exists():
        raise RuntimeError('Deployment already exists; review instead of overwrite')
    backup = Path('/data/singux-backups') / ('services-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(mode=0o700)
    (backup / 'containers.before.json').write_text(json.dumps(before))
    print('IMPORT_IMAGES', flush=True)
    run(['docker', 'load', '-i', str(HERE / 'services-runtime-images-20261009.tar.gz')])
    for tag in ['singux/rcoder:20260929-local', 'singux/computer-runner:20261008-local',
                'singux/file-server:1.5.4-20260929-local', 'nginx:1.25-alpine']:
        image = json.loads(run(['docker', 'image', 'inspect', tag]))[0]
        if image['Os'] != 'linux' or image['Architecture'] != 'amd64':
            raise RuntimeError('Unexpected image platform')
    print('IMAGES_IMPORTED', flush=True)
    key = secrets.token_urlsafe(40)
    rcoder = json.loads((HERE / 'rcoder.production.json').read_text())
    rcoder['api_key_auth'] = {'enabled': True, 'api_key': key}
    (HERE / 'rcoder.private.json').write_text(json.dumps(rcoder, indent=2))
    (HERE / 'rcoder.private.json').chmod(0o600)
    (HERE / 'service-key').write_text(key)
    (HERE / 'service-key').chmod(0o600)
    gateway = (HERE / 'gateway.production.conf').read_text()
    gateway = gateway.replace('proxy_pass $upstream;', 'proxy_pass $upstream;\n      proxy_set_header x-api-key "' + key + '";')
    (HERE / 'gateway.private.conf').write_text(gateway)
    (HERE / 'gateway.private.conf').chmod(0o600)
    WORK.mkdir(parents=True, exist_ok=True)
    for name in ['projects', 'computer', 'templates', 'uploads', 'logs', 'dist']:
        (WORK / name).mkdir(exist_ok=True)
    template_source = Path('/data/singux-update/services-20261009-files-r1/singux-services-files-20261009-r1/templates')
    templates = list(template_source.glob('*.zip'))
    if not templates:
        raise RuntimeError('Staged templates missing')
    for source in templates:
        dest = WORK / 'templates' / source.name
        if not dest.exists():
            shutil.copyfile(source, dest)
            dest.chmod(0o644)
    for p in [WORK, *[WORK / n for n in ['projects', 'computer', 'templates', 'uploads', 'logs', 'dist']]]:
        os.chown(p, 1000, 1000)
        p.chmod(0o750)
    services = {
        'file-server': {
            'image': 'singux/file-server:1.5.4-20260929-local',
            'environment': {'PORT': '60000', 'PROJECT_SOURCE_DIR': '/data/projects',
                'COMPUTER_WORKSPACE_DIR': '/data/computer', 'INIT_PROJECT_DIR': '/data/templates',
                'DIST_TARGET_DIR': '/data/dist', 'UPLOAD_PROJECT_DIR': '/data/uploads', 'LOG_BASE_DIR': '/data/logs'},
            'volumes': [str(WORK) + ':/data'], 'ports': ['127.0.0.1:16000:60000'],
            'mem_limit': '512m', 'memswap_limit': '1g', 'cpus': 0.5,
            'pids_limit': 256, 'networks': {'platform': {'aliases': ['singux-file-service']}, 'runtime': {}}},
        'rcoder': {
            'image': 'singux/rcoder:20260929-local', 'entrypoint': ['/app/bin/rcoder'],
            'command': ['--port', '8090', '--projects-dir', '/data/projects', '--enable-proxy', '--proxy-port', '8088'],
            'working_dir': '/app', 'environment': {'RCODER_PORT': '8090', 'RUST_LOG': 'warn'},
            'volumes': [str(HERE / 'rcoder.private.json') + ':/app/config.yml:ro',
                        str(WORK) + ':/data', '/var/run/docker.sock:/var/run/docker.sock'],
            'ports': ['127.0.0.1:18096:8090'], 'mem_limit': '512m', 'memswap_limit': '1g',
            'cpus': 0.5, 'pids_limit': 256,
            'healthcheck': {'test': ['CMD', 'curl', '-fsS', 'http://127.0.0.1:8090/health'],
                            'interval': '15s', 'timeout': '5s', 'start_period': '30s', 'retries': 5},
            'networks': {'platform': {'aliases': ['singux-rcoder']}, 'runtime': {}}},
        'gateway': {
            'image': 'nginx:1.25-alpine',
            'volumes': [str(HERE / 'gateway.private.conf') + ':/etc/nginx/nginx.conf:ro'],
            'ports': ['127.0.0.1:18088:8088'], 'mem_limit': '64m', 'cpus': 0.25, 'pids_limit': 64,
            'networks': {'platform': {'aliases': ['singux-service-gateway']}}}}
    for service in services.values():
        service.update(restart='unless-stopped', logging={'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}})
    compose = {'services': services, 'networks': {'platform': {'external': True, 'name': 'singux_default'},
                'runtime': {'name': 'singux-execution'}}}
    config_path.write_text(json.dumps(compose, indent=2))
    cmd = ['docker', 'compose', '-p', PROJECT, '-f', str(config_path)]
    run(cmd + ['config', '-q'])
    try:
        run(cmd + ['up', '-d', '--pull', 'never'])
        for _ in range(60):
            state = json.loads(run(['docker', 'inspect', 'singux-runtime-rcoder-1']))[0]['State']
            if state.get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(3)
        else:
            raise RuntimeError('RCoder health failed')
        for url in ['http://127.0.0.1:16000/health', 'http://127.0.0.1:18096/health']:
            with urllib.request.urlopen(url, timeout=20) as response:
                assert response.status == 200
        for name, (cid, image) in platform.items():
            current = json.loads(run(['docker', 'inspect', name]))[0]
            assert current['Id'] == cid and current['Image'] == image and current['State']['Running']
        result = {'status': 'SERVICES_DEPLOYED', 'existingContainersUnchanged': True,
                  'runtimeServices': list(services), 'backup': str(backup),
                  'backendConnected': False, 'publicPortsExposed': False, 'realModelTested': False}
        (HERE / 'deployment-result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except BaseException:
        run(cmd + ['stop'])
        print('NEW_SERVICES_STOPPED; existing services and workspace retained', flush=True)
        raise


if __name__ == '__main__':
    main()
