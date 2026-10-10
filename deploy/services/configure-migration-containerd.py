"""Keep Docker 29 containerd image layers on the verified data disk."""
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True).strip()


assert run('findmnt', '-n', '-o', 'UUID', '/data') == '01ccf5b4-6ec4-468c-9cb7-90b055ad0df9'
assert not run('docker', 'ps', '-aq')
assert not run('docker', 'image', 'ls', '-q')
config = Path('/etc/containerd/config.toml')
assert not config.exists(), 'Refuse existing containerd config'
subprocess.run(['systemctl', 'stop', 'docker.service', 'docker.socket', 'containerd.service'], check=True)
config.parent.mkdir(exist_ok=True)
config.write_text('version = 2\nroot = "/data/containerd"\nstate = "/run/containerd"\n')
dropin = Path('/etc/systemd/system/containerd.service.d')
dropin.mkdir(parents=True, exist_ok=True)
(dropin / 'data-disk.conf').write_text('[Unit]\nRequiresMountsFor=/data\n')
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'start', 'containerd', 'docker'], check=True)
assert run('docker', 'info', '--format', '{{.DockerRootDir}}') == '/data/docker'
assert Path('/data/containerd').is_dir()
print('CONTAINERD_DATA_DISK_READY')
