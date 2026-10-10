"""Transfer the reviewed module only; no credentials or database payload in artifacts."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/data/singux-update/workflow-proxy-20261009-r1'
spec = importlib.util.spec_from_file_location('transport', ROOT / 'deploy/remote-mcp.py')
transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--stage', action='store_true')
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--status', action='store_true'); parser.add_argument('--result', action='store_true')
    args = parser.parse_args()
    client = transport.paramiko.SSHClient(); client.set_missing_host_key_policy(transport.PinnedKey())
    try:
        client.connect('43.136.175.19', username='root', password=os.environ.pop('SINGUX_SSH_PASSWORD'),
                       look_for_keys=False, allow_agent=False, timeout=20)
        if args.status:
            transport.run(client, 'tail -n 10 ' + REMOTE + '/deployment.log'); return
        if args.result:
            transport.run(client, 'cat ' + REMOTE + '/deployment-result.json')
            ftp = client.open_sftp()
            try: ftp.get(REMOTE + '/deployment-result.json', str(ROOT / 'outputs/workflow-production-deployment-20261009.json'))
            finally: ftp.close()
            return
        if args.stage:
            release = ROOT / 'outputs/workflow-proxy-20261009'
            report = json.loads((release / 'release.json').read_text())
            with zipfile.ZipFile(release / 'runtime/app.jar') as jar:
                module = jar.read(report['changedModule'])
            report['moduleSha256'] = hashlib.sha256(module).hexdigest()
            transport.run(client, 'mkdir -p ' + REMOTE)
            ftp = client.open_sftp()
            try:
                ftp.put(str(ROOT / 'deploy/update-workflow-proxy.py'), REMOTE + '/update-workflow-proxy.py')
                ftp.putfo(io.BytesIO(module), REMOTE + '/module.jar')
                ftp.putfo(io.BytesIO(json.dumps(report).encode()), REMOTE + '/release.json')
                for name in ('update-workflow-proxy.py', 'module.jar', 'release.json'): ftp.chmod(REMOTE + '/' + name, 0o600)
            finally: ftp.close()
            transport.run(client, 'python3 ' + REMOTE + '/update-workflow-proxy.py')
        if args.apply:
            launch = '''import pathlib,subprocess
root=pathlib.Path("%s")
assert not (root/"deployment.log").exists(), "Already launched"
with (root/"deployment.log").open("xb") as log:
 p=subprocess.Popen(["python3","-u",str(root/"update-workflow-proxy.py"),"--apply"],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
print("DEPLOY_LAUNCHED pid="+str(p.pid))
''' % REMOTE
            transport.run(client, 'python3 -', launch)
    finally: client.close()

if __name__ == '__main__': main()
