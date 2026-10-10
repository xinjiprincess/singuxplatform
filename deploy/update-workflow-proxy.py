"""Schema-unchanged model factory patch; preserves MCP overlay and rolls back images."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

DEPLOY = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
BASE_SHA = '4afe7428cc11450df8dd39ff028c46659cad3ae364d9cfa0b5cb1e7972b3b7ac'
NEW_SHA = 'aeda06730b81da6feb4d03d16ff0d8888a1f3a00789f3f83ebe75988ba4bd6db'
TAG = 'singux/backend:1.1.10-20261009-workflow-proxy-r1'

def run(args, output=None):
    result = subprocess.run(args, stdout=output if output is not None else subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode: raise RuntimeError('Command failed: ' + ' '.join(args[:3]))
    return result.stdout.decode().strip() if output is None else ''

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4194304), b''): h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--apply', action='store_true'); args = parser.parse_args()
    os.umask(0o077); here = Path(__file__).resolve().parent
    report = json.loads((here / 'release.json').read_text())
    assert report['baselineJarSha256'] == BASE_SHA and report['patchedJarSha256'] == NEW_SHA
    assert sha(here / 'module.jar') == report['moduleSha256']
    compose = ['docker', 'compose', '-p', 'singux', '--env-file', str(DEPLOY / '.env'), '-f', str(DEPLOY / 'compose.json'), '-f', str(DEPLOY / 'compose.mcp.json')]
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
    assert backend['State']['Health']['Status'] == 'healthy'
    assert run(['docker', 'exec', backend['Id'], 'sha256sum', '/app/app.jar']).split()[0] == BASE_SHA
    original = (DEPLOY / 'compose.mcp.json').read_bytes()
    overlay = json.loads(original)
    assert set(overlay['services']) == {'backend', 'mcp-proxy'}
    assert overlay['services']['backend']['environment']['MCP_PROXY_URL'] == 'http://mcp-proxy:8080'
    print('CHECK_OK baseline and MCP override', flush=True)
    if not args.apply: return
    runtime = here / 'runtime'; runtime.mkdir(exist_ok=True)
    run(['docker', 'cp', backend['Id'] + ':/app/app.jar', str(here / 'baseline.jar')])
    assert sha(here / 'baseline.jar') == BASE_SHA
    module = report['changedModule']
    with zipfile.ZipFile(here / 'baseline.jar') as old, zipfile.ZipFile(runtime / 'app.jar', 'w') as new:
        assert module in old.namelist()
        replacement = (here / 'module.jar').read_bytes()
        for item in old.infolist(): new.writestr(copy.copy(item), replacement if item.filename == module else old.read(item))
    assert sha(runtime / 'app.jar') == NEW_SHA, 'Rebuilt JAR checksum differs'
    (runtime / 'Dockerfile').write_text('FROM ' + backend['Image'] + '\nCOPY --chown=app:app app.jar /app/app.jar\n')
    run(['docker', 'build', '--pull=false', '-t', TAG, str(runtime)])
    image = json.loads(run(['docker', 'image', 'inspect', TAG]))[0]
    assert image['Os'] == 'linux' and image['Architecture'] == 'amd64'
    backup = Path('/data/singux-backups') / ('workflow-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True)
    (backup / 'compose.mcp.json').write_bytes(original)
    (backup / 'previous-image.txt').write_text(backend['Image'] + '\n')
    (backup / 'baseline-jar-sha256.txt').write_text(BASE_SHA + '\n')
    stopped = False
    try:
        print('MAINTENANCE_START backup=' + str(backup), flush=True); stopped = True
        run(compose + ['stop', '--timeout', '120', 'frontend', 'backend'])
        with (backup / 'databases.sql').open('wb') as target:
            run(['docker', 'exec', 'singux-mysql-1', 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --all-databases --single-transaction --routines --events --triggers --set-gtid-purged=OFF'], output=target)
        assert (backup / 'databases.sql').stat().st_size > 0
        (backup / 'database.sha256').write_text(sha(backup / 'databases.sql') + '  databases.sql\n')
        overlay['services']['backend']['image'] = image['Id']
        temp = DEPLOY / 'compose.mcp.json.workflow-tmp'
        temp.write_text(json.dumps(overlay, indent=2)); os.replace(temp, DEPLOY / 'compose.mcp.json')
        run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        assert run(['docker', 'exec', 'singux-backend-1', 'sha256sum', '/app/app.jar']).split()[0] == NEW_SHA
        current = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
        def mounts(item): return sorted((m['Type'], m.get('Name', ''), m['Source'], m['Destination'], m['RW']) for m in item['Mounts'])
        assert mounts(current) == mounts(backend)
        run(['python3', '/data/singux-update/mcp-recovery-20261009-r1/verify-production.py'])
        run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', 'frontend'])
        run(compose + ['restart', 'frontend'])
        run(['python3', '/data/singux-update/mcp-recovery-20261009-r1/verify-production.py', '--public'])
        result = {'status': 'DEPLOY_OK', 'image': image['Id'], 'jarSha256': NEW_SHA, 'backup': str(backup), 'schemaChanged': False}
        (here / 'deployment-result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except BaseException:
        if stopped:
            (DEPLOY / 'compose.mcp.json').write_bytes(original)
            run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend', 'frontend'])
            run(compose + ['restart', 'frontend'])
            print('ROLLBACK_OK No database restored.', flush=True)
        raise

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('DEPLOY_ERROR ' + str(error), flush=True); raise SystemExit(1)
