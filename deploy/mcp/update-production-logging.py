"""Schema-free MCP logging update for the pinned single-tenant production baseline."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import zipfile

ROOT = Path('/data/singux-mcp-logging-20261010-r1')
DEPLOY = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
BASE_SHA = 'aeda06730b81da6feb4d03d16ff0d8888a1f3a00789f3f83ebe75988ba4bd6db'


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('MCP logging command failed: ' + ' '.join(args[:3]))
    return result.stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def main():
    os.umask(0o077)
    report = json.loads((ROOT / 'release.json').read_text())
    assert report['baselineJarSha256'] == BASE_SHA and report['schemaUnchanged'] is True
    backend = inspect('singux-backend-1')
    assert backend['State']['Health']['Status'] == 'healthy'
    assert run(['docker', 'exec', backend['Id'], 'sha256sum', '/app/app.jar']).split()[0] == BASE_SHA
    labels = backend['Config']['Labels']
    assert labels['com.docker.compose.project'] == 'singux'
    assert labels['com.docker.compose.project.working_dir'] == str(DEPLOY)
    files = labels['com.docker.compose.project.config_files'].split(',')
    assert all(Path(file).resolve().parent == DEPLOY for file in files)
    overlay = Path(files[-1]); before = overlay.read_bytes()
    config = json.loads(before)
    release = ROOT / 'runtime'
    assert not release.exists(), 'Preserve previous deployment/backup'
    release.mkdir(mode=0o700)
    (ROOT / 'compose.before.json').write_bytes(before)
    (ROOT / 'previous-image.txt').write_text(backend['Image'])
    run(['docker', 'cp', backend['Id'] + ':/app/app.jar', str(ROOT / 'baseline.jar')])
    assert sha(ROOT / 'baseline.jar') == BASE_SHA
    allowed = {'BOOT-INF/lib/app-platform-mcp-application-0.0.1-SNAPSHOT.jar',
               'BOOT-INF/lib/app-platform-mcp-ui-0.0.1-SNAPSHOT.jar'}
    assert set(report['modules']) == allowed
    replacements = {}
    for name, digest in report['modules'].items():
        module = ROOT / Path(name).name
        assert sha(module) == digest
        replacements[name] = module.read_bytes()
    with zipfile.ZipFile(ROOT / 'baseline.jar') as old, zipfile.ZipFile(release / 'app.jar', 'w') as new:
        assert allowed.issubset(old.namelist())
        for item in old.infolist():
            new.writestr(copy.copy(item), replacements.get(item.filename, old.read(item)))
    assert sha(release / 'app.jar') == report['patchedJarSha256']
    (release / 'Dockerfile').write_text('FROM ' + backend['Image'] + '\nCOPY --chown=app:app app.jar /app/app.jar\n')
    run(['docker', 'build', '--pull=false', '-t', report['image'], str(release)])
    cmd = ['docker', 'compose', '-p', 'singux', '--project-directory', str(DEPLOY), '--env-file', str(DEPLOY / '.env')]
    for file in files: cmd += ['-f', file]
    preserved = {name: inspect('singux-' + name + '-1')['Id'] for name in
                 ('mysql', 'redis', 'elasticsearch', 'minio', 'etcd', 'milvus', 'mcp-proxy')}
    try:
        config['services'].setdefault('backend', {})['image'] = report['image']
        overlay.write_text(json.dumps(config, indent=2))
        run(cmd + ['config', '--quiet'])
        print('MCP_LOG_BACKEND_RESTART', flush=True)
        run(cmd + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        current = inspect('singux-backend-1')
        assert run(['docker', 'exec', current['Id'], 'sha256sum', '/app/app.jar']).split()[0] == report['patchedJarSha256']
        def mounts(item):
            return sorted((m['Type'], m.get('Name', ''), m['Source'], m['Destination'], m['RW']) for m in item['Mounts'])
        assert mounts(current) == mounts(backend)
        assert sorted(current['Config']['Env']) == sorted(backend['Config']['Env'])
        assert current['HostConfig']['Memory'] == backend['HostConfig']['Memory']
        assert all(inspect('singux-' + name + '-1')['Id'] == id for name, id in preserved.items())
        # Reload the unchanged frontend only if its static upstream needs the new backend IP.
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        for attempt in range(20):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8080/api/tenant/config', timeout=15) as response:
                    assert json.load(response)['code'] == '0000'
                break
            except Exception:
                if attempt == 19: raise
                time.sleep(3)
    except BaseException:
        overlay.write_bytes(before)
        run(cmd + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        raise
    result = {'status': 'MCP_LOGGING_UPDATED', 'image': report['image'], 'jarSha256': report['patchedJarSha256'],
              'schemaUnchanged': True, 'dataServicesUnchanged': True, 'backup': str(ROOT),
              'businessLogVerification': 'pending'}
    (ROOT / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
