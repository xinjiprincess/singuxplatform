"""Add static documentation to the target baseline without changing business JS."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
RELEASE = ROOT / 'docs-release-20261010'
TAG = 'singux/frontend:1.1.10-20261010-docs-singletenant-r1'


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    assert p.returncode == 0, 'Command failed: ' + ' '.join(args[:3])
    return p.stdout


def main():
    global ROOT, RELEASE, TAG
    os.umask(0o077)
    parameters = json.load(sys.stdin)
    source = parameters.get('mode') == 'source'
    if source:
        ROOT = Path('/data/singux-docs-20261010')
        RELEASE = ROOT / 'release'
        TAG = 'singux/frontend:1.1.10-20261010-docs-singletenant-r1'
    base_url = 'http://127.0.0.1:8080' if source else 'http://127.0.0.1'
    archive = ROOT / 'docs-static-20261010.tar.gz'
    with archive.open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == parameters['sha256']
    assert not RELEASE.exists(), 'Preserve existing documentation release'
    front = json.loads(run(['docker', 'inspect', 'singux-frontend-1']))[0]
    assert front['Config']['Image'] == 'singux/frontend:1.1.10-20261009-filing-r1'
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id']
    labels = front['Config']['Labels']
    path = (Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64/compose.filing.json')
            if source else ROOT / 'compose.app.test.json')
    config = json.loads(path.read_text())
    mounts = [x for x in front['Mounts'] if x['Destination'] == '/etc/nginx/templates/default.conf.template']
    assert len(mounts) == 1 and mounts[0]['Type'] == 'bind'
    template = Path(mounts[0]['Source'])
    allowed = path.parent if source else ROOT
    assert template.is_file() and template.resolve().is_relative_to(allowed)
    original = template.read_text()
    assert 'location ^~ /docs/' not in original and original.count('location / {') == 1
    RELEASE.mkdir(mode=0o700)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            assert member.name == 'docs' or member.name.startswith('docs/')
            assert member.isfile() or member.isdir()
        for member in tar.getmembers():
            destination = (RELEASE / member.name).resolve()
            assert destination.is_relative_to(RELEASE.resolve())
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as inp, destination.open('xb') as out:
                    shutil.copyfileobj(inp, out)
    assert (RELEASE / 'docs/index.html').is_file()
    (RELEASE / 'Dockerfile').write_text('FROM singux/frontend:1.1.10-20261009-filing-r1\n'
        'COPY docs/ /usr/share/nginx/html/docs/\nRUN chmod -R a+rX /usr/share/nginx/html/docs\n')
    (RELEASE / 'compose.before.json').write_text(path.read_text())
    (RELEASE / 'nginx.before.template').write_text(original)
    run(['docker', 'build', '-t', TAG, str(RELEASE)])
    locations = 'location = /docs { return 308 /docs/; }\n    location ^~ /docs/ {\n'
    locations += '        root /usr/share/nginx/html; index index.html;\n'
    locations += '        try_files $uri $uri/ =404;\n        add_header X-Content-Type-Options nosniff;\n    }\n    '
    config['services']['frontend']['image'] = TAG
    cmd = ['docker', 'compose', '-p', 'singux', '-f', str(path)]
    if source:
        assert labels['com.docker.compose.project'] == 'singux'
        files = labels['com.docker.compose.project.config_files'].split(',')
        assert files[-1] == str(path)
        assert all(Path(f).is_file() and Path(f).parent == path.parent for f in files)
        cmd = ['docker', 'compose', '-p', 'singux', '--project-directory', str(path.parent),
               '--env-file', str(path.parent / '.env')]
        for f in files:
            cmd += ['-f', f]
    menu = None
    try:
        template.write_text(original.replace('location / {', locations + 'location / {'))
        path.write_text(json.dumps(config, indent=2))
        run(cmd + ['config', '--quiet'])
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-t'])
        with urllib.request.urlopen(base_url + '/docs/assets/manual.json', timeout=30) as r:
            manual = json.load(r)
        assert manual['sections']
        with urllib.request.urlopen(base_url + '/docs/download/manual.pdf', timeout=30) as r:
            assert r.read(5) == b'%PDF-'
        token = ''

        def api(route, body=None):
            q = urllib.request.Request(base_url + route,
                data=json.dumps(body).encode() if body is not None else None,
                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
            with urllib.request.urlopen(q, timeout=45) as r:
                result = json.load(r)
            assert result.get('code') == '0000', 'Documentation menu API rejected'
            return result.get('data')

        token = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': parameters.pop('password')})['token']
        menu = api('/api/system/menu/code/documents')
        assert menu['code'] == 'documents'
        (RELEASE / 'menu.before.json').write_text(json.dumps(menu, indent=2))
        api('/api/system/menu/update', {'id': menu['id'], 'path': '/docs/',
                                      'icon': 'icons-nav-doc', 'openType': 1, 'status': 1})
        assert api('/api/system/menu/code/documents')['path'] == '/docs/'
        assert json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id'] == backend
        record = {'status': 'DOCS_DEPLOYED', 'image': TAG, 'menuPath': '/docs/',
                  'sections': len(manual['sections']), 'backendUnchanged': True,
                  'sourceChanged': source, 'dnsChanged': False, 'sha256': parameters['sha256']}
        (ROOT / 'docs-deployment-result.json').write_text(json.dumps(record, indent=2))
        print(json.dumps(record), flush=True)
    except BaseException:
        if menu is not None:
            try:
                api('/api/system/menu/update', {k: menu[k] for k in
                    ['id', 'path', 'icon', 'openType', 'status'] if k in menu})
            except Exception:
                (RELEASE / 'menu-rollback-required.json').write_text(json.dumps({'menuId': menu['id']}))
        path.write_text((RELEASE / 'compose.before.json').read_text())
        template.write_text(original)
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        raise


if __name__ == '__main__':
    main()
