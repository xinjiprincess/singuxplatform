"""Forced SSH receiver for private business archives; never starts a platform."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.umask(0o077)
root = Path('/data/singux-migration-20261009')
comment = 'singux-migration-business-20261009'
try:
    partial = root / 'business.tar.gz.part'
    digest = hashlib.sha256()
    with partial.open('wb') as f:
        while chunk := sys.stdin.buffer.read(1024 * 1024):
            f.write(chunk)
            digest.update(chunk)
    subprocess.run(['gzip', '-t', str(partial)], check=True)
    archive = root / 'business.tar.gz'
    partial.rename(archive)
    (root / 'business-receive-result.json').write_text(json.dumps({
        'status': 'BUSINESS_ARCHIVE_STAGED', 'sha256': digest.hexdigest(),
        'bytes': archive.stat().st_size, 'restored': False, 'sourceSnapshotConsistencyVerified': False,
        'note': 'Compare source export result/hash and review live-file warnings before restoring.'}, indent=2))
except BaseException:
    (root / 'business-receive-result.json').write_text(json.dumps({'status': 'BUSINESS_RECEIVE_FAILED'}))
    raise
finally:
    auth = Path('/root/.ssh/authorized_keys')
    lines = auth.read_text().splitlines()
    auth.write_text('\n'.join(x for x in lines if not x.endswith(' ' + comment)) + '\n')
    auth.chmod(0o600)
