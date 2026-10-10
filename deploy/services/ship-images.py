"""Export tested service images and upload with pinned SSH and resumable checksum verification."""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
TAGS = ['singux/rcoder:20260929-local', 'singux/computer-runner:20261008-local',
        'singux/file-server:1.5.4-20260929-local', 'nginx:1.25-alpine']
REMOTE = '/data/singux-update/services-runtime-20261009-r1'


def main():
    archive = ROOT / 'outputs/services-runtime-images-20261009.tar.gz'
    if not archive.exists():
        partial = archive.with_suffix('.partial')
        proc = subprocess.Popen(['docker', 'save', *TAGS], stdout=subprocess.PIPE)
        try:
            with gzip.open(partial, 'wb', compresslevel=1) as out:
                while True:
                    chunk = proc.stdout.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            if proc.wait() != 0:
                raise RuntimeError('Docker export failed')
            partial.replace(archive)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    expected = digest.hexdigest()
    print('EXPORT_OK bytes=' + str(archive.stat().st_size), flush=True)
    spec = importlib.util.spec_from_file_location('transport', ROOT / 'deploy/remote-mcp.py')
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    client = transport.paramiko.SSHClient()
    client.set_missing_host_key_policy(transport.PinnedKey())
    client.connect('43.136.175.19', username='root', password=os.environ.pop('SINGUX_SSH_PASSWORD'),
                   look_for_keys=False, allow_agent=False, timeout=30)
    client.get_transport().set_keepalive(20)
    try:
        transport.run(client, 'mkdir -p ' + REMOTE)
        ftp = client.open_sftp()
        ftp.chmod(REMOTE, 0o700)
        target = REMOTE + '/' + archive.name
        try:
            offset = ftp.stat(target + '.partial').st_size
        except IOError:
            offset = 0
        if offset > archive.stat().st_size:
            raise RuntimeError('Remote partial larger than archive')
        last = time.monotonic()
        with archive.open('rb') as source, ftp.open(target + '.partial', 'ab') as dest:
            source.seek(offset)
            dest.set_pipelined(True)
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                dest.write(chunk)
                offset += len(chunk)
                if time.monotonic() - last > 30:
                    print('UPLOAD bytes=' + str(offset) + '/' + str(archive.stat().st_size), flush=True)
                    last = time.monotonic()
        ftp.close()
        output = transport.run(client, 'python3 -',
            'import hashlib,pathlib\np=pathlib.Path(' + repr(target + '.partial') + ')\n'
            'h=hashlib.sha256()\nwith p.open("rb") as f:\n'
            ' for b in iter(lambda:f.read(4194304),b""):h.update(b)\n'
            'assert h.hexdigest()==' + repr(expected) + '\n'
            'p.rename(' + repr(target) + ')\nprint("UPLOAD_VERIFIED")\n')
        record = {'sha256': expected, 'bytes': archive.stat().st_size, 'remote': target,
                  'images': TAGS, 'deployed': False}
        (ROOT / 'outputs/services-runtime-transfer-20261009.json').write_text(json.dumps(record, indent=2))
        print(output, flush=True)
    finally:
        client.close()


if __name__ == '__main__':
    main()
