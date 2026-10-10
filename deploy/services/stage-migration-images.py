"""Copy verified production images directly between pinned hosts; no service stop."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('transport', ROOT / 'deploy/remote-mcp.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
SOURCE = '43.136.175.19'
TARGET = '113.219.170.192'
PIN = 'SHA256:OokadZfIM867aOLgYBCfZGXG/VpT8s183Gdv3EDhSIo'
REMOTE = '/data/singux-migration-20261009'
KEY = '/root/singux-migration-20261009-key'
IMAGES = [
    'singux/frontend:1.1.10-20261009-filing-r1',
    'singux/backend:1.1.10-20261009-workflow-proxy-r1',
    'singux/mcp-proxy:0.2.8-20261009-recovery-r1',
    'singux/computer-runner:20261008-local', 'singux/rcoder:20260929-local',
    'singux/file-server:1.5.4-20260929-local', 'nginx:1.25-alpine',
    'mysql:8.4', 'redis:7-alpine', 'bitnami/elasticsearch:8.18.0',
    'minio/minio:RELEASE.2025-04-22T22-12-26Z',
    'quay.io/coreos/etcd:v3.5.18', 'milvusdb/milvus:v2.5.4',
    'singu-download-site:1.0.0',
]


class Pinned(t.paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        actual = 'SHA256:' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
        assert actual == (t.PIN if hostname == SOURCE else PIN), 'Host key mismatch'


def execute(client, command, timeout=120):
    _, out, err = client.exec_command(command, timeout=timeout)
    result = out.read().decode()
    error = err.read().decode()
    if out.channel.recv_exit_status():
        raise RuntimeError('Remote command failed: ' + error[-1000:])
    return result.strip()


def write(client, path, data):
    with client.open_sftp() as ftp:
        with ftp.open(path, 'w') as f:
            f.write(data)
        ftp.chmod(path, 0o600)


def main():
    password = os.environ.pop('SINGUX_SSH_PASSWORD')
    clients = []
    auth_line = None
    try:
        for host in (SOURCE, TARGET):
            c = t.paramiko.SSHClient()
            c.set_missing_host_key_policy(Pinned())
            c.connect(host, username='root', password=password, look_for_keys=False, allow_agent=False, timeout=20)
            c.get_transport().set_keepalive(20)
            clients.append(c)
        password = None
        old, new = clients
        expected = json.loads(execute(old, 'docker image inspect ' + ' '.join(map(shlex.quote, IMAGES))))
        manifest = {name: item['Id'] for name, item in zip(IMAGES, expected)}
        for c in clients:
            execute(c, 'umask 077; mkdir ' + REMOTE)
        execute(old, 'test ! -e ' + KEY + ' && ssh-keygen -q -t ed25519 -N "" -f ' + KEY)
        public = execute(old, 'cat ' + KEY + '.pub')
        key = new.get_transport().get_remote_server_key()
        write(old, REMOTE + '/known_hosts', TARGET + ' ' + key.get_name() + ' ' + key.get_base64() + '\n')
        auth_line = 'restrict,from="' + SOURCE + '",command="cat > ' + REMOTE + '/images.tar.gz.part" ' + public
        execute(new, 'umask 077; mkdir -p /root/.ssh; chmod 700 /root/.ssh; touch /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys')
        with new.open_sftp() as ftp:
            with ftp.open('/root/.ssh/authorized_keys', 'a') as f:
                f.write('\n' + auth_line + '\n')
        write(new, REMOTE + '/images.json', json.dumps(manifest, indent=2))
        ssh = 'ssh -i ' + KEY + ' -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=' + REMOTE + '/known_hosts -o ServerAliveInterval=20 root@' + TARGET
        pipeline = 'set -o pipefail; umask 077; docker save ' + ' '.join(map(shlex.quote, IMAGES)) + ' | nice -n 10 gzip -1 | tee ' + REMOTE + '/images.tar.gz | ' + ssh
        _, out, err = old.exec_command('bash -c ' + shlex.quote(pipeline), timeout=7200)
        start = time.monotonic()
        while not out.channel.exit_status_ready():
            print('IMAGE_STREAM elapsed_seconds=' + str(int(time.monotonic() - start)), flush=True)
            time.sleep(30)
        error = err.read().decode()
        assert out.channel.recv_exit_status() == 0, 'Image stream failed: ' + error[-1000:]
        source_sha = execute(old, 'sha256sum ' + REMOTE + '/images.tar.gz').split()[0]
        target_sha = execute(new, 'sha256sum ' + REMOTE + '/images.tar.gz.part').split()[0]
        assert source_sha == target_sha, 'Transfer checksum mismatch'
        execute(new, 'mv ' + REMOTE + '/images.tar.gz.part ' + REMOTE + '/images.tar.gz')
        print('IMAGE_TRANSFER_VERIFIED sha256=' + source_sha, flush=True)
        print(execute(new, 'docker load -i ' + REMOTE + '/images.tar.gz', timeout=3600), flush=True)
        actual = json.loads(execute(new, 'docker image inspect ' + ' '.join(map(shlex.quote, IMAGES))))
        assert {name: item['Id'] for name, item in zip(IMAGES, actual)} == manifest
        record = {'status': 'IMAGES_STAGED', 'source': SOURCE, 'target': TARGET,
                  'sha256': source_sha, 'images': manifest, 'servicesStarted': False,
                  'businessDataMigrated': False, 'sourceServicesStopped': False}
        (ROOT / 'outputs/migration-images-20261009.json').write_text(json.dumps(record, indent=2))
        write(new, REMOTE + '/images-result.json', json.dumps(record, indent=2))
        print('IMAGES_STAGED images=' + str(len(IMAGES)), flush=True)
    finally:
        if len(clients) == 2 and auth_line:
            new = clients[1]
            with new.open_sftp() as ftp:
                with ftp.open('/root/.ssh/authorized_keys') as f:
                    current = f.read().decode()
                cleaned = '\n'.join(line for line in current.split('\n') if line != auth_line)
                with ftp.open('/root/.ssh/authorized_keys', 'w') as f:
                    f.write(cleaned)
                ftp.chmod('/root/.ssh/authorized_keys', 0o600)
        if clients:
            execute(clients[0], 'rm -f ' + KEY + ' ' + KEY + '.pub')
        for c in clients:
            c.close()


if __name__ == '__main__':
    main()
