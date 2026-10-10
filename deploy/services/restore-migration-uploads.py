"""Copy verified staged uploads to a new target volume without starting backend."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/data/singux-migration-20261009')
VOLUME = 'singux_backend-uploads'


def inventory(root):
    files = {}
    for path in root.rglob('*'):
        assert not path.is_symlink(), 'Unexpected upload link; review before copying'
        assert path.is_dir() or path.is_file(), 'Special upload entry refused'
        if path.is_file():
            with path.open('rb') as source:
                files[path.relative_to(root).as_posix()] = {
                    'bytes': path.stat().st_size,
                    'sha256': hashlib.file_digest(source, 'sha256').hexdigest()}
    return files


def main():
    os.umask(0o077)
    assert json.loads((ROOT / 'mysql-restore-result.json').read_text())['status'] == 'MYSQL_RESTORED'
    assert json.loads((ROOT / 'business-staging-result.json').read_text())['status'] == 'BUSINESS_CORE_STAGED'
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True).splitlines()
    assert 'singux-backend-1' not in names, 'Refuse restoring into a used backend'
    volumes = subprocess.check_output(['docker', 'volume', 'ls', '-q'], text=True).splitlines()
    assert VOLUME not in volumes, 'Preserve existing volume; inspect partial restore before retry'
    source = ROOT / 'business-staged/backend-uploads'
    expected = inventory(source)
    assert expected, 'Unexpected empty upload export'
    total = sum(item['bytes'] for item in expected.values())
    assert shutil.disk_usage(ROOT).free > total + 1024**3
    subprocess.run(['docker', 'volume', 'create', '--label', 'com.docker.compose.project=singux',
                    '--label', 'com.docker.compose.volume=backend-uploads', VOLUME],
                   stdout=subprocess.DEVNULL, check=True)
    volume = json.loads(subprocess.check_output(['docker', 'volume', 'inspect', VOLUME]))[0]
    docker_root = Path(subprocess.check_output(['docker', 'info', '--format', '{{.DockerRootDir}}'], text=True).strip())
    destination = Path(volume['Mountpoint'])
    assert destination.resolve() == (docker_root / 'volumes' / VOLUME / '_data').resolve()
    assert not any(destination.iterdir()), 'Volume unexpectedly nonempty'
    shutil.copytree(source, destination, dirs_exist_ok=True)
    assert inventory(destination) == expected, 'Upload hash verification failed'
    (ROOT / 'uploads-file-manifest.json').write_text(json.dumps(expected, indent=2))
    record = {'status': 'UPLOADS_VOLUME_RESTORED', 'volume': VOLUME,
              'files': len(expected), 'bytes': total, 'allFileHashesMatched': True,
              'sourceChanged': False, 'targetBackendStarted': False, 'notLatestSourceSnapshot': True}
    (ROOT / 'uploads-restore-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
