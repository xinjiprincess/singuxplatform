"""Fix only the target restored upload volume for its actual Java UID/GID."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path('/data/singux-migration-20261009')


def main():
    os.umask(0o077)
    spec = importlib.util.spec_from_file_location('uploads', ROOT / 'restore-migration-uploads.py')
    uploads = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(uploads)
    uid = int(subprocess.check_output(['docker', 'exec', 'singux-backend-1', 'id', '-u']))
    gid = int(subprocess.check_output(['docker', 'exec', 'singux-backend-1', 'id', '-g']))
    processes = subprocess.check_output(['docker', 'exec', 'singux-backend-1', 'ps', '-eo', 'uid,gid,comm'], text=True)
    assert any(line.split() == [str(uid), str(gid), 'java'] for line in processes.splitlines())
    obj = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
    mount = next(m for m in obj['Mounts'] if m['Destination'] == '/data/uploads')
    assert mount['Type'] == 'volume' and mount['Name'] == uploads.VOLUME
    volume = json.loads(subprocess.check_output(['docker', 'volume', 'inspect', uploads.VOLUME]))[0]
    destination = Path(volume['Mountpoint'])
    docker_root = Path(subprocess.check_output(['docker', 'info', '--format', '{{.DockerRootDir}}'], text=True).strip())
    assert destination.resolve() == (docker_root / 'volumes' / uploads.VOLUME / '_data').resolve()
    before = uploads.inventory(destination)
    expected = json.loads((ROOT / 'uploads-file-manifest.json').read_text())
    assert all(before.get(k) == v for k, v in expected.items()), 'Restored source files changed; review first'
    backup = ROOT / 'uploads-permissions-before.json'
    assert not backup.exists(), 'Preserve previous permission audit'
    paths = [destination, *destination.rglob('*')]
    original = {}
    for path in paths:
        assert not path.is_symlink()
        info = path.stat()
        original[str(path.relative_to(destination))] = {'uid': info.st_uid, 'gid': info.st_gid,
                                                        'mode': stat.S_IMODE(info.st_mode)}
    backup.write_text(json.dumps(original, indent=2))
    for path in paths:
        os.chown(path, uid, gid)
        path.chmod(stat.S_IMODE(path.stat().st_mode) | (0o700 if path.is_dir() else 0o600))
    after = uploads.inventory(destination)
    assert before == after, 'Content changed during permission repair'
    subprocess.run(['docker', 'exec', 'singux-backend-1', 'sh', '-c',
                    'test -r /data/uploads && test -w /data/uploads && test -x /data/uploads'], check=True)
    record = {'status': 'UPLOAD_PERMISSIONS_REPAIRED', 'uid': uid, 'gid': gid,
              'verifiedFiles': len(expected), 'allOriginalHashesUnchanged': True, 'sourceChanged': False}
    (ROOT / 'upload-permissions-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
