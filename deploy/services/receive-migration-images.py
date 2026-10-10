"""Forced SSH command: receive and validate image staging without starting services."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.umask(0o077)
root = Path('/data/singux-migration-20261009')
result = root / 'background-images-result.json'
key_comment = 'singux-migration-background-20261009'
try:
    part = root / 'background-images.tar.gz.part'
    digest = hashlib.sha256()
    with part.open('wb') as output:
        while chunk := sys.stdin.buffer.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    subprocess.run(['gzip', '-t', str(part)], check=True)
    archive = root / 'background-images.tar.gz'
    part.rename(archive)
    subprocess.run(['docker', 'load', '-i', str(archive)], check=True)
    expected = json.loads((root / 'images.json').read_text())
    images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', *expected], text=True))
    actual = {name: item['Id'] for name, item in zip(expected, images)}
    assert len(images) == len(expected) and actual == expected
    result.write_text(json.dumps({'status': 'IMAGES_STAGED', 'sha256': digest.hexdigest(),
                                 'imageCount': len(expected), 'businessDataMigrated': False,
                                 'servicesStarted': False}, indent=2))
except BaseException:
    result.write_text(json.dumps({'status': 'IMAGE_STAGE_FAILED', 'servicesStarted': False}))
    raise
finally:
    auth = Path('/root/.ssh/authorized_keys')
    lines = auth.read_text().splitlines()
    auth.write_text('\n'.join(line for line in lines if not line.endswith(' ' + key_comment)) + '\n')
    auth.chmod(0o600)
