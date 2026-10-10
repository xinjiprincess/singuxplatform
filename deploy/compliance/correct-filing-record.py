"""Correct the production HTML shell without restarting any running service."""
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
DEST = Path('/root/singux-filing-correction-20261011')
OLD = '蜀ICP备2026030409号'
NEW = '蜀ICP备2026053509号'
TAG = 'singux/frontend:1.1.10-20261011-filing-corrected-r1'


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    os.umask(0o077)
    assert run('hostname') == 'VM-0-15-opencloudos'
    before = json.loads(run('docker', 'inspect', 'singux-frontend-1'))[0]
    assert before['Config']['Image'] == 'singux/frontend:1.1.10-20261010-docs-singletenant-r2'
    assert not any(m['Destination'].startswith('/usr/share/nginx/html') for m in before['Mounts'])
    DEST.mkdir(mode=0o700, exist_ok=True)
    assert not (DEST / 'result.json').exists()
    override = ROOT / 'compose.filing.json'
    config = json.loads(override.read_text())
    assert config['services']['frontend']['image'] == before['Config']['Image']
    original = run('docker', 'exec', 'singux-frontend-1', 'cat', '/usr/share/nginx/html/index.html')
    assert original.count(OLD) == 1 and NEW not in original
    (DEST / 'index.before.html').write_text(original)
    (DEST / 'compose.filing.before.json').write_bytes(override.read_bytes())
    updated = original.replace(OLD, NEW)
    index = DEST / 'index.html'
    index.write_text(updated)
    index.chmod(0o644)
    (DEST / 'Dockerfile').write_text('FROM ' + before['Image'] + '\nCOPY index.html /usr/share/nginx/html/index.html\n')
    run('docker', 'build', '--network', 'none', '--pull=false', '-t', TAG, str(DEST))
    try:
        config['services']['frontend']['image'] = TAG
        override.write_text(json.dumps(config, indent=2))
        command = ['docker', 'compose', '-p', 'singux', '--env-file', str(ROOT / '.env')]
        for file in before['Config']['Labels']['com.docker.compose.project.config_files'].split(','):
            command.extend(['-f', file])
        run(*command, 'config', '-q')
        run('docker', 'cp', str(index), 'singux-frontend-1:/usr/share/nginx/html/index.filing-next.html')
        run('docker', 'exec', 'singux-frontend-1', 'mv', '/usr/share/nginx/html/index.filing-next.html', '/usr/share/nginx/html/index.html')
        with urllib.request.urlopen('http://127.0.0.1:8080/login', timeout=20) as response:
            html = response.read().decode()
        assert NEW in html and OLD not in html
        current = json.loads(run('docker', 'inspect', 'singux-frontend-1'))[0]
        assert current['Id'] == before['Id'] and current['Mounts'] == before['Mounts']
    except BaseException:
        override.write_bytes((DEST / 'compose.filing.before.json').read_bytes())
        (DEST / 'index.before.html').chmod(0o644)
        run('docker', 'cp', str(DEST / 'index.before.html'), 'singux-frontend-1:/usr/share/nginx/html/index.html')
        raise
    result = {'status': 'FILING_CORRECTED', 'record': NEW, 'persistentImage': TAG,
              'liveContainerRecreated': False, 'businessBundlesChanged': False,
              'note': 'Live HTML replaced atomically; Compose uses corrected image on next recreation.'}
    (DEST / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
