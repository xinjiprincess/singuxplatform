"""Pinned SSH transport for read-only preflight and resumable release upload."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tmp/ssh-diagnostic-libs'))
import paramiko

PIN = 'SHA256:j9wQITtHH7ZeO7fVw7wgQUzj6JaMiHgmNOg0+S2ttxU'
REMOTE = '/data/singux-update/mcp-recovery-20261009-r1'
PACKAGE = ROOT / 'outputs/singux-service-recovery-mcp-singletenant-20261009.tar.gz'
SHA = 'f1a70ba8a75e00df14c1a024ca9752e9a7ac4c4043d88cd007cadbb7c9fca303'

class PinnedKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        actual = 'SHA256:' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
        if key.get_name() != 'ssh-ed25519' or actual != PIN:
            raise paramiko.SSHException('Verified host key mismatch')

def run(client, command, source=None):
    stdin, stdout, stderr = client.exec_command(command, timeout=120)
    if source is not None:
        stdin.write(source); stdin.flush(); stdin.channel.shutdown_write()
    output = stdout.read().decode()
    if stdout.channel.recv_exit_status() != 0:
        # Do not expose unrestricted remote diagnostics or interpolated secrets.
        raise RuntimeError('Remote operation failed; no production configuration changed by this transport')
    print(output.strip(), flush=True)
    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--upload', action='store_true')
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--deploy', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--result', action='store_true')
    parser.add_argument('--inspect-images', action='store_true')
    parser.add_argument('--scripts-only', action='store_true')
    parser.add_argument('--retry', action='store_true')
    args = parser.parse_args()
    client = paramiko.SSHClient(); client.set_missing_host_key_policy(PinnedKey())
    password = os.environ.pop('SINGUX_SSH_PASSWORD')
    try:
        client.connect('43.136.175.19', username='root', password=password,
                       look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20)
        password = None
        client.get_transport().set_keepalive(20)
        if args.result:
            result = json.loads(run(client, 'cat ' + shlex.quote(REMOTE + '/deployment-result.json')))
            if result.get('status') != 'DEPLOY_OK': raise RuntimeError('Deployment did not succeed')
            ftp = client.open_sftp()
            try:
                ftp.get(REMOTE + '/deployment-result.json', str(ROOT / 'outputs/mcp-production-deployment-20261009.json'))
            finally: ftp.close()
            run(client, "docker ps --format '{{.Names}} {{.Status}}'")
            run(client, "docker stats --no-stream --format '{{.Name}} memory={{.MemUsage}} pids={{.PIDs}}' singux-mcp-proxy-1")
            return
        if args.inspect_images:
            run(client, "docker image inspect singux/backend:1.1.10-20261009-service-recovery-mcp-r1 singux/mcp-proxy:0.2.8-20261009-recovery-r1 --format '{{json .Id}} {{json .Os}} {{json .Architecture}} {{json .RepoDigests}}'")
            return
        if args.status:
            run(client, 'tail -n 16 ' + shlex.quote(REMOTE + '/deployment.log'))
            return
        if args.stage:
            ftp = client.open_sftp()
            try:
                for name in ('check-production.py', 'update-production.py', 'verify-production.py', 'smoke-call.mjs'):
                    ftp.put(str(ROOT / 'deploy/mcp' / name), REMOTE + '/' + name)
                    ftp.chmod(REMOTE + '/' + name, 0o600)
            finally: ftp.close()
            if args.scripts_only:
                run(client, 'python3 ' + shlex.quote(REMOTE + '/update-production.py'))
                return
            prepare = '''import hashlib, pathlib, tarfile
root=pathlib.Path("%s")
archive=root/"%s"
h=hashlib.sha256()
with archive.open("rb") as f:
    for chunk in iter(lambda:f.read(4*1024*1024),b""):h.update(chunk)
assert h.hexdigest()=="%s", "Archive checksum mismatch"
with tarfile.open(archive,"r:gz") as tar:
    for member in tar:
        parts=pathlib.PurePosixPath(member.name).parts
        assert member.isfile() and len(parts)==2 and parts[0]=="singux-service-recovery-mcp-singletenant-20261009"
        assert parts[1] in {"images.tar","images.json","release.json","compose.mcp.json","mcp-sources.json","README.md","SHA256SUMS"}
        tar.extract(member,str(root))
print("STAGE_OK archive_verified=True")
''' % (REMOTE, PACKAGE.name, SHA)
            run(client, 'python3 -', prepare)
            run(client, 'python3 ' + shlex.quote(REMOTE + '/update-production.py'))
            return
        if args.deploy:
            launch = '''import pathlib,subprocess
root=pathlib.Path("%s")
retry=%s
if retry:
    text=(root/"deployment.log").read_text()
    assert "DEPLOY_ERROR" in text and ("MAINTENANCE_START" not in text or "ROLLBACK_OK" in text), "Retry requires a reviewed failure with completed rollback"
    archived=root/"deployment-import-check-failed.log"
    if archived.exists(): archived=root/("deployment-rolled-back-"+__import__('datetime').datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S')+".log")
    (root/"deployment.log").rename(archived)
assert not (root/"deployment.log").exists(), "Deployment already launched; inspect status"
with (root/"deployment.log").open("xb") as log:
    process=subprocess.Popen(["python3","-u",str(root/"update-production.py"),"--apply"],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
print("DEPLOY_LAUNCHED pid="+str(process.pid))
''' % (REMOTE, repr(args.retry))
            run(client, 'python3 -', launch)
            return
        run(client, 'python3 -', (ROOT / 'deploy/mcp/check-production.py').read_text(encoding='utf-8'))
        if not args.upload: return
        run(client, 'umask 077; mkdir -p ' + shlex.quote(REMOTE))
        remote_file = REMOTE + '/' + PACKAGE.name
        part = remote_file + '.part'
        ftp = client.open_sftp(); ftp.get_channel().settimeout(120)
        try:
            try: offset = ftp.stat(part).st_size
            except IOError: offset = 0
            if offset > PACKAGE.stat().st_size: raise RuntimeError('Oversized partial upload')
            # Resume only if the already uploaded prefix matches the local archive.
            if offset:
                digest = hashlib.sha256()
                with PACKAGE.open('rb') as stream:
                    remaining = offset
                    while remaining:
                        chunk = stream.read(min(4 * 1024 * 1024, remaining))
                        digest.update(chunk); remaining -= len(chunk)
                remote_hash = run(client, 'head -c {} {} | sha256sum'.format(offset, shlex.quote(part))).split()[0]
                if remote_hash != digest.hexdigest(): raise RuntimeError('Partial upload checksum mismatch')
            last = time.monotonic()
            with PACKAGE.open('rb') as local, ftp.open(part, 'ab' if offset else 'wb') as remote:
                local.seek(offset); remote.set_pipelined(True)
                while True:
                    chunk = local.read(256 * 1024)
                    if not chunk: break
                    remote.write(chunk); offset += len(chunk)
                    if time.monotonic() - last >= 30:
                        print('UPLOAD {}/{} bytes'.format(offset, PACKAGE.stat().st_size), flush=True)
                        last = time.monotonic()
            actual = run(client, 'sha256sum ' + shlex.quote(part)).split()[0]
            if actual != SHA: raise RuntimeError('Uploaded archive checksum mismatch')
            ftp.rename(part, remote_file)
            print('UPLOAD_OK ' + remote_file, flush=True)
        finally: ftp.close()
    finally: client.close()

if __name__ == '__main__': main()
