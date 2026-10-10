"""Prepare online object and configuration exports; does not copy live database volumes."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/data/singux-migration-20261009')
BASE = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
RUNTIME = Path('/data/singux-update/services-runtime-20261009-r1')
TMP = '/tmp/singux-migration-export-20261009'


def main():
    os.umask(0o077)
    staging = ROOT / 'business-export'
    staging.mkdir(mode=0o700, exist_ok=False)
    configs = staging / 'configs'
    configs.mkdir()
    originals = [BASE / name for name in ['compose.json', 'compose.mcp.json', 'compose.runtime.json',
                                          'compose.filing.json', '.env', 'default-model-proxy.conf.template']]
    originals += [RUNTIME / name for name in ['compose.runtime.json', 'rcoder.private.json', 'gateway.private.conf']]
    for source in originals:
        assert source.is_file() and not source.is_symlink()
        destination = configs / source.relative_to('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(0o600)
    compose = ['docker', 'compose', '-p', 'singux', '--env-file', str(BASE / '.env')]
    for name in ['compose.json', 'compose.mcp.json', 'compose.runtime.json', 'compose.filing.json']:
        compose += ['-f', str(BASE / name)]
    merged = subprocess.check_output(compose + ['config', '--format', 'json'])
    (configs / 'platform-resolved.json').write_bytes(merged)
    containers = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-minio-1']))
    assert containers[0]['State']['Running']
    bootstrap = ('set -eu; test ! -e ' + TMP + '; mkdir -m 700 ' + TMP +
                 '; mc --config-dir ' + TMP + '/config alias set source http://127.0.0.1:9000 '
                 '"$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null')
    subprocess.run(['docker', 'exec', 'singux-minio-1', 'sh', '-c', bootstrap], check=True)
    mc = ['docker', 'exec', 'singux-minio-1', 'mc', '--config-dir', TMP + '/config']
    listing = subprocess.check_output(mc + ['ls', '--json', 'source'], text=True)
    buckets = [json.loads(line)['key'].rstrip('/') for line in listing.splitlines() if line.strip()]
    assert all(name and '/' not in name and name not in {'.', '..'} for name in buckets)
    objects = staging / 'minio-objects'
    objects.mkdir()
    with (staging / 'minio-export.log').open('wb') as log:
        for name in buckets:
            subprocess.run(mc + ['mirror', '--json', 'source/' + name, TMP + '/objects/' + name],
                           stdout=log, stderr=log, check=True)
        if buckets:
            subprocess.run(['docker', 'cp', 'singux-minio-1:' + TMP + '/objects/.', str(objects)], check=True,
                           stdout=log, stderr=log)
    (staging / 'minio-buckets.json').write_text(json.dumps(buckets))
    subprocess.run(['docker', 'exec', 'singux-minio-1', 'rm', '-f', TMP + '/config/config.json'], check=True)
    for name in ['application-databases.sql.gz', 'mysql-export.json']:
        shutil.copy2(ROOT / name, staging / name)
    shutil.copytree(ROOT / 'search-export-v2', staging / 'search')
    report = {'status': 'OBJECTS_AND_CONFIGS_EXPORTED', 'bucketCount': len(buckets),
              'sourceWritesPaused': False, 'crossStoreConsistent': False,
              'filesExported': False, 'allBusinessDataMigrated': False}
    (staging / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
