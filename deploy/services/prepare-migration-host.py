"""Initialize the verified empty migration disk and install Ubuntu Docker packages."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    assert os.geteuid() == 0
    assert 'VERSION_ID="24.04"' in Path('/etc/os-release').read_text()
    device = '/dev/vdb'
    disk = json.loads(run('lsblk', '-J', '-b', '-o', 'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT', device))['blockdevices'][0]
    assert disk['type'] == 'disk' and 99 * 1024**3 < int(disk['size']) < 101 * 1024**3
    assert not disk.get('children') and not disk.get('mountpoint') and not disk.get('fstype')
    signatures = json.loads(run('wipefs', '--json', device)).get('signatures', [])
    assert not signatures, 'Refuse disk with existing signatures'
    assert not Path('/var/lib/docker').exists(), 'Refuse existing Docker installation'
    target = Path('/data')
    assert not target.is_symlink()
    if target.exists():
        assert not list(target.iterdir()), 'Refuse non-empty /data'
    target.mkdir(exist_ok=True)
    assert subprocess.run(['mountpoint', '-q', '/data']).returncode != 0
    subprocess.run(['mkfs.ext4', device], check=True)
    uuid = run('blkid', '-s', 'UUID', '-o', 'value', device)
    backup = Path('/root/singux-migration-preparation')
    backup.mkdir(mode=0o700, exist_ok=False)
    shutil.copy2('/etc/fstab', backup / 'fstab.before')
    with open('/etc/fstab', 'a') as f:
        f.write('\nUUID=' + uuid + ' /data ext4 defaults 0 2\n')
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['mount', '/data'], check=True)
    assert run('findmnt', '-n', '-o', 'UUID', '/data') == uuid
    Path('/etc/docker').mkdir(exist_ok=True)
    config = Path('/etc/docker/daemon.json')
    assert not config.exists(), 'Refuse existing daemon configuration'
    config.write_text(json.dumps({'data-root': '/data/docker', 'log-driver': 'json-file',
                                 'log-opts': {'max-size': '20m', 'max-file': '3'}}, indent=2) + '\n')
    dropin = Path('/etc/systemd/system/docker.service.d')
    dropin.mkdir(parents=True, exist_ok=True)
    (dropin / 'data-disk.conf').write_text('[Unit]\nRequiresMountsFor=/data\n')
    subprocess.run(['apt-get', 'update'], check=True)
    env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    subprocess.run(['apt-get', 'install', '-y', 'docker.io', 'docker-compose-v2', 'rsync', 'zstd'], check=True, env=env)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'docker'], check=True)
    assert run('docker', 'info', '--format', '{{.DockerRootDir}}') == '/data/docker'
    print(run('docker', 'compose', 'version'), flush=True)
    print('MIGRATION_HOST_READY data=/data docker=/data/docker', flush=True)


if __name__ == '__main__':
    main()
