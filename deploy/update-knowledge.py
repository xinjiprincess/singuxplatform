"""Production-only, schema-unchanged knowledge hotfix. Default mode is read-only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

PROJECT = 'singux'
IMAGE = 'singux/backend:1.1.10-20261007-knowledge-singletenant-r1'
BASE_MANIFEST = 'sha256:aeccd376f79829d4d1ecd95083f08c9259af4bb2ca1ef4df8e8d8566b874bdaa'
BASE_CONFIG = 'sha256:ab096327316a8d31a7cb1c9e3e764cd251213336de66a233b3d5b9720519eb47'
BASE_JAR = '9dfbfd86d5bae9ff8d49b34141d7a75cbda2d8820d57519544dec7d0499061e7'

def run(args, stdout=None):
    result = subprocess.run(args, stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        # Docker/Compose diagnostics can expose interpolated credentials.
        raise RuntimeError('Command failed (exit {}): {}'.format(result.returncode, ' '.join(args[:3])))
    return result.stdout.decode().strip() if stdout is None else ''

def sha(path):
    value = hashlib.sha256()
    with open(str(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def inspect(containers):
    return json.loads(run(['docker', 'inspect'] + containers))

def atomic_json(path, value):
    temporary = path.with_name(path.name + '.knowledge-tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.chmod(str(temporary), 0o600)
    os.replace(str(temporary), str(path))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('deployment', type=Path)
    parser.add_argument('release', type=Path)
    parser.add_argument('--apply', action='store_true', help='Confirm maintenance window, backup and application replacement')
    args = parser.parse_args()
    os.umask(0o077)
    deployment = args.deployment.resolve()
    release = args.release.resolve()
    compose_path = deployment / 'compose.json'
    if not compose_path.is_file() or not (deployment / '.env').is_file():
        raise RuntimeError('Existing compose.json and .env required')
    compose = ['docker', 'compose', '-p', PROJECT, '--project-directory', str(deployment),
               '--env-file', str(deployment / '.env'), '-f', str(compose_path)]
    manifest = json.loads((release / 'release.json').read_text())
    if manifest.get('image') != IMAGE or manifest.get('schemaUnchanged') is not True or manifest.get('dataBackwardCompatible') is not True:
        raise RuntimeError('Unsupported release manifest')
    if manifest.get('baselineJarSha256') != BASE_JAR or sha(release / 'runtime/app.jar') != manifest['patchedJarSha256']:
        raise RuntimeError('Executable JAR checksum mismatch')
    original = json.loads(compose_path.read_text())
    run(compose + ['config', '--quiet'])
    ids = run(compose + ['ps', '-q']).split()
    containers = inspect(ids) if ids else []
    services = {}
    volumes = set()
    for item in containers:
        labels = item['Config'].get('Labels') or {}
        service = labels.get('com.docker.compose.service')
        if labels.get('com.docker.compose.project') != PROJECT or item['State']['Status'] != 'running':
            raise RuntimeError('Unexpected container project or state')
        if service in services:
            raise RuntimeError('Multiple running containers for one service')
        if Path(labels.get('com.docker.compose.project.working_dir', '')).resolve() != deployment:
            raise RuntimeError('Deployment directory does not match container labels')
        for mount in item['Mounts']:
            if mount['Type'] == 'volume':
                volumes.add(mount['Name'])
            elif mount.get('RW'):
                raise RuntimeError('Writable bind mount requires a separately reviewed backup plan')
            if service == 'backend' and mount['Destination'].startswith('/app'):
                raise RuntimeError('Backend executable is overridden by a mount')
        services[service] = item
    if not {'frontend', 'backend', 'mysql', 'elasticsearch', 'milvus', 'etcd', 'minio', 'redis'} <= set(services):
        raise RuntimeError('All expected production services must be running')
    for service in ('backend', 'frontend', 'mysql'):
        if services[service]['State'].get('Health', {}).get('Status') != 'healthy':
            raise RuntimeError('Existing service must be healthy before update: ' + service)
    backend = services['backend']
    if backend['Image'] not in (BASE_MANIFEST, BASE_CONFIG):
        raise RuntimeError('Production backend image changed; do not apply this patch')
    actual = run(['docker', 'exec', backend['Id'], 'sha256sum', '/app/app.jar']).split()[0]
    if actual != BASE_JAR:
        raise RuntimeError('Running backend executable differs from verified baseline')
    uploads = [m for m in backend['Mounts'] if m['Destination'] == '/data/uploads']
    if len(uploads) != 1 or uploads[0].get('Name') != 'singux_backend-uploads':
        raise RuntimeError('Unexpected uploads volume')
    backup_root = Path('/data/singux-backups')
    if not os.path.ismount('/data'):
        raise RuntimeError('/data is not mounted; refusing to use the system disk')
    size_kib = 0
    for volume in sorted(volumes):
        run(['docker', 'volume', 'inspect', volume])
        size_kib += int(run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--read-only', '--user', '0',
                             '--entrypoint', 'sh', '--mount', 'type=volume,source={},target=/source,readonly'.format(volume),
                             backend['Image'], '-c', 'du -sk /source']).split()[0])
    required = size_kib * 1024 * 2 + 3 * 1024 ** 3
    if shutil.disk_usage('/data').free < required:
        raise RuntimeError('Insufficient backup/build space on /data (require {} bytes)'.format(required))
    print('CHECK_OK project={} services={} volumes={} backup_space_required={}'.format(PROJECT, len(services), len(volumes), required), flush=True)
    if not args.apply:
        print('Read-only check complete. No service was stopped or replaced.')
        return
    lock = deployment / '.knowledge-update-lock'
    lock.mkdir()
    old_handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Update interrupted')
    for name in ('SIGTERM', 'SIGHUP'):
        if hasattr(signal, name):
            number = getattr(signal, name)
            old_handlers[number] = signal.signal(number, interrupted)
    backup = backup_root / ('knowledge-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid()))
    stopped = False
    try:
        backup.mkdir(parents=True)
        shutil.copy2(str(compose_path), str(backup / 'original-compose.json'))
        shutil.copy2(str(deployment / '.env'), str(backup / '.env'))
        for config in ('original-compose.json', '.env'):
            os.chmod(str(backup / config), 0o600)
        rollback = json.loads(json.dumps(original))
        for service, item in services.items():
            rollback['services'][service]['image'] = item['Image']
        atomic_json(backup / 'rollback-compose.json', rollback)
        atomic_json(backup / 'runtime.json', {'images': {s: v['Image'] for s, v in services.items()}, 'volumes': sorted(volumes)})
        stopped = True
        print('MAINTENANCE_START backup={}'.format(backup), flush=True)
        run(compose + ['stop', '--timeout', '120', 'backend'])
        with open(str(backup / 'databases.sql'), 'wb') as target:
            run(['docker', 'exec', services['mysql']['Id'], 'sh', '-c',
                 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --all-databases --single-transaction --routines --events --triggers --set-gtid-purged=OFF'], stdout=target)
        if not (backup / 'databases.sql').stat().st_size:
            raise RuntimeError('Database backup is empty')
        run(compose + ['stop', '--timeout', '120'] + list(services))
        for volume in sorted(volumes):
            archive = backup / (volume + '.tar.gz')
            print('BACKUP_VOLUME {}'.format(volume), flush=True)
            with open(str(archive), 'wb') as target:
                run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--read-only', '--user', '0',
                     '--entrypoint', 'sh', '--mount', 'type=volume,source={},target=/source,readonly'.format(volume),
                     backend['Image'], '-c', 'tar --numeric-owner --xattrs --acls -czpf - -C /source .'], stdout=target)
            run(['tar', '-tzf', str(archive)], stdout=subprocess.DEVNULL)
        files = [p for p in backup.iterdir() if p.is_file()]
        atomic_json(backup / 'backup-checksums.json', {p.name: sha(p) for p in files})
        (backup / 'BACKUP_COMPLETE').write_text('Archive readability and checksums verified; full restore drill remains operator responsibility.\n')
        base_tag = 'singux/backend:knowledge-baseline-20261007'
        run(['docker', 'tag', backend['Image'], base_tag])
        run(['docker', 'build', '--pull=false', '-t', IMAGE, str(release / 'runtime')])
        # Pin the new image to its actual local ID, not a mutable tag.
        next_config = json.loads(json.dumps(original))
        next_config['services']['backend']['image'] = json.loads(run(['docker', 'image', 'inspect', IMAGE]))[0]['Id']
        atomic_json(compose_path, next_config)
        run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600'] + list(services))
        # Nginx can retain the previous backend container IP until restarted.
        run(compose + ['restart', 'frontend'])
        run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '120', 'frontend'])
        new_backend = run(compose + ['ps', '-q', 'backend'])
        if run(['docker', 'exec', new_backend, 'sha256sum', '/app/app.jar']).split()[0] != manifest['patchedJarSha256']:
            raise RuntimeError('Running executable is not the patched JAR')
        print('UPDATE_OK image={} backup={}'.format(IMAGE, backup))
        print('Verify login, model calls, upload and knowledge operations. Copy backup off-host. No database/volume data rollback was performed.')
    except BaseException:
        if stopped:
            print('UPDATE_FAILED attempting image/config rollback; never overwriting database or volumes.', file=sys.stderr)
            try:
                rollback_file = backup / 'rollback-compose.json'
                if rollback_file.is_file():
                    atomic_json(compose_path, json.loads(rollback_file.read_text()))
                run(compose + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600'] + list(services))
                run(compose + ['restart', 'frontend'])
                print('IMAGE_ROLLBACK_OK backup={}'.format(backup), file=sys.stderr)
            except Exception:
                print('ROLLBACK_FAILED operator intervention required; backup={}'.format(backup), file=sys.stderr)
        raise
    finally:
        for number, handler in old_handlers.items():
            signal.signal(number, handler)
        lock.rmdir()

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
