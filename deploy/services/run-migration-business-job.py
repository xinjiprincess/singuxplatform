"""Source-side online file archive and encrypted direct transfer."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

os.umask(0o077)
root = Path('/data/singux-migration-20261009')
key = '/root/singux-migration-business-20261009-key'
result = root / 'business-export-result.json'
try:
    assert json.loads((root / 'business-export/search/result.json').read_text())['status'] == 'LOGICAL_EXPORT_READY'
    result.write_text(json.dumps({'status': 'BUSINESS_STREAM_RUNNING', 'pid': os.getpid(),
                                  'sourceWritesPaused': False}))
    tar = ['tar', '--numeric-owner', '--one-file-system', '--transform=flags=r;s,^_data,backend-uploads,',
           '-cf', '-', '-C', str(root), 'business-export',
           '-C', '/var/lib/docker/volumes/singux_backend-uploads', '_data',
           '-C', '/data/singux-services', 'workspace',
           '-C', '/opt', 'singu-download-site/data', 'singu-download-site/releases']
    ssh = ['ssh', '-T', '-i', key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
           '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(root / 'known_hosts'),
           '-o', 'ServerAliveInterval=20', 'root@113.219.170.192']
    archive = root / 'business.tar.gz'
    command = ('set -o pipefail; ' + shlex.join(tar) + ' | nice -n 10 gzip -1 | tee ' +
               shlex.quote(str(archive)) + ' | ' + shlex.join(ssh))
    # tar returns nonzero if a source file changes; that must not be called a consistent backup.
    subprocess.run(['bash', '-c', command], check=True)
    digest = hashlib.sha256()
    with archive.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    result.write_text(json.dumps({'status': 'BUSINESS_STREAM_COMPLETE', 'sha256': digest.hexdigest(),
                                  'sourceWritesPaused': False, 'crossStoreConsistent': False,
                                  'allBusinessDataMigrated': False}, indent=2))
except BaseException:
    result.write_text(json.dumps({'status': 'BUSINESS_EXPORT_FAILED', 'allBusinessDataMigrated': False,
                                  'note': 'Check private log; possible live-file change or transfer failure.'}))
    raise
finally:
    Path(key).unlink(missing_ok=True)
    Path(key + '.pub').unlink(missing_ok=True)
