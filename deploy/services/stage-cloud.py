"""Upload a checksummed, explicitly non-deployable service reference bundle.

This transport has no apply/start/build/import operation. Credentials are read
from the environment and never included in the bundle.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
REMOTE = '/data/singux-update/services-20261009-files-r1'
NAME = 'singux-services-files-20261009-r1'
FILES = [
    'deploy/services/compose.local.yml', 'deploy/services/rcoder.yml',
    'deploy/services/gateway.conf', 'deploy/services/connect-local-backend.py',
    'deploy/services/register-local.py', 'deploy/services/check-local.py',
    'deploy/services/prepare-checks.py', 'deploy/services/check-preview.cjs',
    'deploy/services/stage-cloud.py', 'deploy/file-server.Dockerfile',
    'deploy/rcoder-local-runtime.Dockerfile', 'deploy/computer-runner/Dockerfile',
    'deploy/computer-runner/start.sh', 'deploy/computer-runner/check-desktop.cjs',
    'deploy/mcp/test-recovery.ps1', 'deploy/mcp/smoke-call.mjs',
    'tests/test_local_service_connection.py', 'docs/runtime-recovery-and-updates.md',
    'VERSION_CHANGES.md', 'outputs/services-local-check-20261009.json',
    'outputs/services-desktop-20261009.png', 'outputs/services-web-preview-20261009.png',
]
IMAGES = ['singux/rcoder:20260929-local', 'singux/computer-runner:20261008-local',
          'singux/file-server:1.5.4-20260929-local',
          'singux/mcp-proxy:0.2.8-20261009-recovery-r1', 'nginx:1.25-alpine']


def package():
    content = {name: (ROOT / name).read_bytes() for name in FILES}
    for name in ['react-vite-template.zip', 'vue3-vite-template.zip']:
        content['templates/' + name] = (Path('D:/singuxplatform/rcoder/docker/project_init') / name).read_bytes()
    images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', *IMAGES], text=True))
    image_records = [{'tags': image['RepoTags'], 'id': image['Id'], 'os': image['Os'],
                     'architecture': image['Architecture']} for image in images]
    content['README.txt'] = b'''FILES ONLY - NO SERVICES ENABLED
This archive contains reviewed LOCAL reference configuration, build scripts,
test records and templates. It does not contain Docker image layers, user data,
passwords, .env files, SSH keys or API tokens. productionApproved=false.
Do not run compose.local.yml on this server: it contains Windows paths and a
local network name. Do not run local registration or backend replacement scripts.
Existing production containers, database and configuration are not modified.
Before activation: review Linux paths/networks, import verified images, provide
capacity (16 GB RAM recommended), enforce concurrency/admission limits, configure
authorized desktop and preview proxy access, protect the Docker control plane,
back up configuration/data and test rollback. Provider 401/403 and complete
business workflows are not certified by these infrastructure tests.
The upstream desktop image is a local test image, not a hardened production image.
'''
    release = {'name': NAME, 'mode': 'FILES_ONLY', 'productionApproved': False,
               'imagesIncluded': False, 'images': image_records,
               'files': {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}}
    content['release.json'] = json.dumps(release, indent=2).encode()
    content['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                 for name, data in sorted(content.items())).encode()
    archive = ROOT / 'outputs' / (NAME + '.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for name, data in sorted(content.items()):
            entry = tarfile.TarInfo(NAME + '/' + name)
            entry.size = len(data)
            entry.mode = 0o600
            tar.addfile(entry, io.BytesIO(data))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='ascii')
    print('PACKAGE_OK bytes=' + str(archive.stat().st_size) + ' sha256=' + digest, flush=True)
    return archive, digest


def upload(archive, digest):
    spec = importlib.util.spec_from_file_location('transport', ROOT / 'deploy/remote-mcp.py')
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    client = transport.paramiko.SSHClient()
    client.set_missing_host_key_policy(transport.PinnedKey())
    try:
        client.connect('43.136.175.19', username='root', password=os.environ.pop('SINGUX_SSH_PASSWORD'),
                       look_for_keys=False, allow_agent=False, timeout=20)
        client.get_transport().set_keepalive(20)
        before = transport.run(client, "docker ps --no-trunc --format '{{.ID}} {{.Image}}' | sort")
        transport.run(client, 'umask 077; mkdir -p ' + shlex.quote(REMOTE))
        ftp = client.open_sftp()
        try:
            ftp.get_channel().settimeout(60)
            ftp.put(str(archive), REMOTE + '/' + archive.name + '.part')
            ftp.chmod(REMOTE + '/' + archive.name + '.part', 0o600)
        finally:
            ftp.close()
        source = '''import hashlib,json,pathlib,tarfile,subprocess
root=pathlib.Path(%r)
archive=root/%r
assert hashlib.sha256(archive.read_bytes()).hexdigest()==%r, 'Archive digest mismatch'
destination=root/%r
assert not destination.exists(), 'Existing stage directory must not be overwritten'
with tarfile.open(archive,'r:gz') as tar:
 members=tar.getmembers()
 for member in members:
  parts=pathlib.PurePosixPath(member.name).parts
  assert member.isfile() and len(parts)>1 and parts[0]==%r
  assert '..' not in parts and not pathlib.PurePosixPath(member.name).is_absolute()
 tar.extractall(root,members=members)
manifest=json.loads((destination/'release.json').read_text())
assert manifest['mode']=='FILES_ONLY' and manifest['productionApproved'] is False and not manifest['imagesIncluded']
for name,digest in manifest['files'].items():
 assert hashlib.sha256((destination/name).read_bytes()).hexdigest()==digest, 'File digest mismatch'
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=destination,check=True,stdout=subprocess.DEVNULL)
archive.rename(root/%r)
memory={line.split(':')[0]:int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
print(json.dumps({'status':'FILES_SYNCED_NOT_ENABLED','directory':str(destination),'archiveSha256':%r,'verifiedFiles':len(manifest['files']),'imagesIncluded':False,'memory':memory}))
''' % (REMOTE, archive.name + '.part', digest, NAME, NAME, archive.name, digest)
        result_text = transport.run(client, 'python3 -', source)
        after = transport.run(client, "docker ps --no-trunc --format '{{.ID}} {{.Image}}' | sort")
        if before != after:
            raise RuntimeError('Container inventory changed during file staging; inspect before any activation')
        result = json.loads(result_text.splitlines()[-1])
        result['containersUnchanged'] = True
        (ROOT / 'outputs/services-cloud-stage-20261009.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('SYNC_OK containers_unchanged=True services_enabled=False')
    finally:
        client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    archive, digest = package()
    if args.upload:
        upload(archive, digest)
