"""Build an HTML-shell-only frontend patch on the running single-tenant baseline."""
import datetime
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
DEPLOY = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
TAG = 'singux/frontend:1.1.10-20261009-filing-r1'
BASE = 'singux/frontend:1.1.10-20260928-entry-fix'


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:3]))
    return result.stdout.strip()


def main():
    os.umask(0o077)
    frontend = json.loads(run(['docker', 'inspect', 'singux-frontend-1']))[0]
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
    baseline = json.loads(run(['docker', 'image', 'inspect', BASE]))[0]
    if frontend['Image'] != baseline['Id']:
        raise RuntimeError('Unexpected production frontend baseline')
    files = backend['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
    if files != [str(DEPLOY / name) for name in ['compose.json', 'compose.mcp.json', 'compose.runtime.json']]:
        raise RuntimeError('Unexpected active Compose files')
    override = DEPLOY / 'compose.filing.json'
    if override.exists():
        raise RuntimeError('Filing override already exists; review required')
    before = json.loads(run(['docker', 'inspect', *run(['docker', 'ps', '-q']).split()]))
    backup = Path('/data/singux-backups') / ('filing-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(mode=0o700)
    (backup / 'containers.before.json').write_text(json.dumps(before))
    for file in [*files, str(DEPLOY / '.env')]:
        shutil.copy2(file, backup / Path(file).name)
    original = run(['docker', 'exec', 'singux-frontend-1', 'cat', '/usr/share/nginx/html/index.html'])
    (backup / 'index.before.html').write_text(original, encoding='utf-8')
    patch = runpy.run_path(str(HERE / 'patch-index.py'))['patch']
    updated = patch(original, (HERE / 'footer.html').read_text(encoding='utf-8'))
    (HERE / 'index.html').write_text(updated, encoding='utf-8')
    # Keep the served static assets world-readable inside the image.
    (HERE / 'index.html').chmod(0o644)
    (HERE / 'footer.css').chmod(0o644)
    (HERE / 'Dockerfile').write_text('FROM ' + BASE + '\nCOPY index.html /usr/share/nginx/html/index.html\nCOPY footer.css /usr/share/nginx/html/singux-filing-20261009.css\n')
    run(['docker', 'build', '--pull=false', '-t', TAG, str(HERE)])
    print('FILING_IMAGE_BUILT; original business bundles unchanged', flush=True)
    cmd = ['docker', 'compose', '-p', 'singux', '--env-file', str(DEPLOY / '.env')]
    for file in files:
        cmd += ['-f', file]
    next_cmd = cmd + ['-f', str(override)]
    try:
        override.write_text(json.dumps({'services': {'frontend': {'image': TAG}}}, indent=2))
        run(next_cmd + ['config', '-q'])
        run(next_cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        for _ in range(45):
            current = json.loads(run(['docker', 'inspect', 'singux-frontend-1']))[0]
            if current['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(2)
        else:
            raise RuntimeError('Frontend health failed')
        assert current['Mounts'] == frontend['Mounts']
        for item in before:
            if item['Name'] == '/singux-frontend-1':
                continue
            now = json.loads(run(['docker', 'inspect', item['Name']]))[0]
            assert now['Id'] == item['Id'] and now['Image'] == item['Image'] and now['State']['Running']
        with urllib.request.urlopen('http://127.0.0.1:8080/login', timeout=20) as response:
            assert '蜀ICP备2026053509号' in response.read().decode()
        result = {'status': 'FILING_DEPLOYED', 'image': TAG, 'imageId': current['Image'],
                  'backup': str(backup), 'businessBundlesUnchanged': True,
                  'otherContainersUnchanged': True, 'frontendMountsPreserved': True}
        (HERE / 'deployment-result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except BaseException:
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        if override.exists():
            override.rename(backup / 'failed.compose.filing.json')
        raise


if __name__ == '__main__':
    main()
