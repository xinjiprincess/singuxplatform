"""Source-side durable image export; all service containers remain running."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

os.umask(0o077)
root = Path('/data/singux-migration-20261009')
key = '/root/singux-migration-background-20261009-key'
record = root / 'background-export-result.json'
try:
    images = json.loads((root / 'images.json').read_text())
    ssh = ['ssh', '-i', key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
           '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(root / 'known_hosts'),
           '-o', 'ServerAliveInterval=20', 'root@113.219.170.192']
    archive = root / 'background-images.tar.gz'
    pipeline = ('set -o pipefail; docker save ' + shlex.join(images) +
                ' | nice -n 10 gzip -1 | tee ' + shlex.quote(str(archive)) + ' | ' + shlex.join(ssh))
    record.write_text(json.dumps({'status': 'IMAGE_STREAM_RUNNING', 'pid': os.getpid()}))
    subprocess.run(['bash', '-c', pipeline], check=True)
    digest = hashlib.sha256()
    with archive.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    record.write_text(json.dumps({'status': 'IMAGE_STREAM_COMPLETE', 'sha256': digest.hexdigest(),
                                 'imageCount': len(images)}, indent=2))
except BaseException:
    record.write_text(json.dumps({'status': 'IMAGE_STREAM_FAILED'}))
    raise
finally:
    Path(key).unlink(missing_ok=True)
    Path(key + '.pub').unlink(missing_ok=True)
