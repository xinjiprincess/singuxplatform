"""Reviewed schema-unchanged deployment; backs up all data and rolls back images on failure."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import subprocess
import sys
import tarfile

BACKEND_TAG = 'singux/backend:1.1.10-20261009-service-recovery-mcp-r1'
MCP_TAG = 'singux/mcp-proxy:0.2.8-20261009-recovery-r1'
JAR_SHA = '4afe7428cc11450df8dd39ff028c46659cad3ae364d9cfa0b5cb1e7972b3b7ac'

def run(args, output=None, source=None):
    result = subprocess.run(args, input=source.encode() if source is not None else None,
                            stdout=output if output is not None else subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:3]))
    return result.stdout.decode().strip() if output is None else ''

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()

def atomic(path, value):
    temp = path.with_name(path.name + '.mcp-tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.chmod(0o600); os.replace(str(temp), str(path))

def image_ids(release, expected):
    # Classic Docker reports the config ID; containerd may report the OCI manifest ID.
    allowed = {expected['id']}
    with tarfile.open(release / 'images.tar', 'r:') as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        rows = [row for row in manifest if expected['tag'] in (row.get('RepoTags') or [])]
        if len(rows) != 1: raise RuntimeError('Archive tag is missing or duplicated')
        config = archive.extractfile(rows[0]['Config']).read()
        if 'sha256:' + hashlib.sha256(config).hexdigest() != expected['id']:
            raise RuntimeError('Archive image config digest mismatch')
        index = json.load(archive.extractfile('index.json'))
        for descriptor in index['manifests']:
            digest = descriptor['digest']
            if not digest.startswith('sha256:') or len(digest) != 71: raise RuntimeError('Invalid OCI digest')
            blob = archive.extractfile('blobs/sha256/' + digest[7:]).read()
            if 'sha256:' + hashlib.sha256(blob).hexdigest() != digest:
                raise RuntimeError('OCI manifest checksum mismatch')
            parsed = json.loads(blob)
            if parsed.get('config', {}).get('digest') == expected['id']: allowed.add(digest)
    return allowed

def counts(mysql):
    tables = ['user', 'space_user', 'knowledge_config', 'knowledge_document', 'skill_config', 'mcp_config']
    query = 'START TRANSACTION READ ONLY;\n' + '\n'.join(
        "SELECT '{}',COUNT(*) FROM `{}`;".format(name, name) for name in tables) + '\nCOMMIT;'
    raw = run(['docker', 'exec', '-i', mysql, 'sh', '-c',
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B agent_platform'], source=query)
    return {line.split('\t')[0]: int(line.split('\t')[1]) for line in raw.splitlines()}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    here = Path(__file__).resolve().parent
    release = here / 'singux-service-recovery-mcp-singletenant-20261009'
    context = runpy.run_path(str(here / 'check-production.py'))
    deployment, services, volumes, backend, compose = [context[k] for k in ('DEPLOY', 'services', 'volumes', 'backend', 'compose')]
    for line in (release / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if Path(name).name != name or sha(release / name) != expected: raise RuntimeError('Release checksum mismatch')
    manifest = json.loads((release / 'release.json').read_text())
    if manifest['baselineJarSha256'] != context['BASE_JAR'] or manifest['patchedJarSha256'] != JAR_SHA:
        raise RuntimeError('Release JAR manifest does not match reviewed revision')
    if manifest.get('schemaUnchanged') is not True: raise RuntimeError('Database migrations are not allowed')
    original = json.loads((deployment / 'compose.json').read_text())
    if (deployment / 'compose.mcp.json').exists(): raise RuntimeError('Existing MCP override requires review')
    if not args.apply:
        print('DEPLOY_CHECK_OK No service stopped or replaced.', flush=True); return
    lock = deployment / '.mcp-recovery-lock'; lock.mkdir()
    backup = Path('/data/singux-backups') / ('mcp-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    stopped = False
    next_compose = compose + ['-f', str(deployment / 'compose.mcp.json')]
    handlers = {}
    def interrupted(signum, frame): raise KeyboardInterrupt('Deployment interrupted')
    for name in ('SIGTERM', 'SIGINT', 'SIGHUP'):
        number = getattr(signal, name); handlers[number] = signal.signal(number, interrupted)
    try:
        print('IMPORT_IMAGES', flush=True)
        run(['docker', 'load', '-i', str(release / 'images.tar')])
        expected_images = json.loads((release / 'images.json').read_text())['images']
        if {v['tag'] for v in expected_images} != {BACKEND_TAG, MCP_TAG}: raise RuntimeError('Unexpected image set')
        loaded = {}
        for expected in expected_images:
            item = json.loads(run(['docker', 'image', 'inspect', expected['tag']]))[0]
            if item['Id'] not in image_ids(release, expected) or item['Os'] != 'linux' or item['Architecture'] != 'amd64':
                raise RuntimeError('Imported image digest or architecture mismatch')
            loaded[expected['tag']] = item['Id']
        backup.mkdir(parents=True)
        shutil.copy2(str(deployment / 'compose.json'), str(backup / 'original-compose.json'))
        shutil.copy2(str(deployment / '.env'), str(backup / '.env'))
        for name in ('original-compose.json', '.env'): (backup / name).chmod(0o600)
        rollback = json.loads(json.dumps(original))
        for name, item in services.items(): rollback['services'][name]['image'] = item['Image']
        atomic(backup / 'rollback-compose.json', rollback)
        atomic(backup / 'runtime.json', {'images': {n: v['Image'] for n, v in services.items()}, 'volumes': sorted(volumes)})
        print('MAINTENANCE_START backup=' + str(backup), flush=True); stopped = True
        run(compose + ['stop', '--timeout', '120', 'frontend', 'backend'])
        before = counts(services['mysql']['Id']); atomic(backup / 'counts-before.json', before)
        with (backup / 'databases.sql').open('wb') as target:
            run(['docker', 'exec', services['mysql']['Id'], 'sh', '-c',
                 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --all-databases --single-transaction --routines --events --triggers --set-gtid-purged=OFF'], output=target)
        if not (backup / 'databases.sql').stat().st_size: raise RuntimeError('SQL backup is empty')
        run(compose + ['stop', '--timeout', '120'] + list(services))
        for volume in sorted(volumes):
            print('BACKUP_VOLUME ' + volume, flush=True)
            path = backup / (volume + '.tar.gz')
            with path.open('wb') as target:
                run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--read-only', '--user', '0',
                     '--entrypoint', 'sh', '--mount', 'type=volume,source={},target=/source,readonly'.format(volume),
                     backend['Image'], '-c', 'tar --numeric-owner --xattrs --acls -czpf - -C /source .'], output=target)
            run(['tar', '-tzf', str(path)], output=subprocess.DEVNULL)
        atomic(backup / 'backup-checksums.json', {p.name: sha(p) for p in backup.iterdir() if p.is_file()})
        (backup / 'BACKUP_COMPLETE').write_text('Backups readable and checksummed. Full restore drill not performed.\n')
        overlay = json.loads((release / 'compose.mcp.json').read_text())
        overlay['services']['backend']['image'] = loaded[BACKEND_TAG]
        overlay['services']['mcp-proxy']['image'] = loaded[MCP_TAG]
        # Production has many pending installations; bound workers and leave subprocess headroom.
        overlay['services']['mcp-proxy'].setdefault('environment', {})['TOKIO_WORKER_THREADS'] = '2'
        overlay['services']['mcp-proxy']['pids_limit'] = 512
        overlay['services']['mcp-proxy']['mem_limit'] = '1536m'
        atomic(deployment / 'compose.mcp.json', overlay)
        run(next_compose + ['config', '--quiet'])
        infra = [n for n in services if n not in ('backend', 'frontend')]
        run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600'] + infra)
        if counts(services['mysql']['Id']) != before: raise RuntimeError('Data counts changed before application startup')
        run(next_compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '180', 'mcp-proxy'])
        run(next_compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        new_backend = run(next_compose + ['ps', '-q', 'backend'])
        if run(['docker', 'exec', new_backend, 'sha256sum', '/app/app.jar']).split()[0] != JAR_SHA:
            raise RuntimeError('Unexpected running JAR')
        run(['docker', 'exec', new_backend, 'curl', '-fsS', '--max-time', '10', 'http://mcp-proxy:8080/health'])
        run(['python3', str(here / 'verify-production.py')])
        print('MCP_TOOL_CALL_OK', flush=True)
        after = counts(services['mysql']['Id']); atomic(backup / 'counts-after.json', after)
        if after != before: raise RuntimeError('Business row counts changed unexpectedly')
        run(next_compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '120', 'frontend'])
        run(next_compose + ['restart', 'frontend'])
        for name, old in services.items():
            new_id = run(next_compose + ['ps', '-q', name])
            current = json.loads(run(['docker', 'inspect', new_id]))[0]
            def mounts(item):
                return sorted((m['Type'], m.get('Name', ''), m['Source'], m['Destination'], m['RW']) for m in item['Mounts'])
            if mounts(current) != mounts(old): raise RuntimeError('Data mounts changed: ' + name)
        print('DATA_COUNTS_AND_MOUNTS_OK', flush=True)
        run(['python3', str(here / 'verify-production.py'), '--public'])
        print('PUBLIC_ROUTES_OK', flush=True)
        result = {'status': 'DEPLOY_OK', 'backup': str(backup), 'counts': after, 'images': loaded,
                  'schemaChanged': False, 'dataRollbackPerformed': False}
        atomic(here / 'deployment-result.json', result)
        print(json.dumps(result), flush=True)
    except BaseException:
        if stopped:
            print('DEPLOY_FAILED Attempting image/config rollback; never restoring over current database.', flush=True)
            try:
                atomic(deployment / 'compose.json', json.loads((backup / 'rollback-compose.json').read_text()))
                # Only this run's newly created override is removed; no data or volumes are deleted.
                override = deployment / 'compose.mcp.json'
                if override.exists(): override.unlink()
                if 'singux-mcp-proxy-1' in run(['docker', 'ps', '--format', '{{.Names}}']).splitlines():
                    run(['docker', 'stop', '--time', '30', 'singux-mcp-proxy-1'])
                run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600'] + list(services))
                run(compose + ['restart', 'frontend'])
                print('ROLLBACK_OK backup=' + str(backup), flush=True)
            except Exception: print('ROLLBACK_FAILED manual intervention required: ' + str(backup), flush=True)
        raise
    finally:
        for number, handler in handlers.items(): signal.signal(number, handler)
        lock.rmdir()

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('DEPLOY_ERROR ' + str(error), flush=True); sys.exit(1)
