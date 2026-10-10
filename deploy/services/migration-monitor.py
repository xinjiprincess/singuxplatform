"""Read-only, loopback-only migration monitor with pinned SSH hosts."""
import argparse
import getpass
import importlib.util
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('migration', ROOT / 'deploy/services/stage-migration-images.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PAGE = Path(__file__).with_name('migration-monitor.html')
lock = threading.Lock()
state = {'updated': None, 'error': None}

# Only allowlisted status fields leave the SSH collector; never expose configs or logs.
REMOTE_CHECK = '''import json, pathlib, subprocess
r=pathlib.Path('/data/singux-migration-20261009')
out={'files':{},'records':{},'containers':[]}
for name in ['background-images.tar.gz.part','background-images.tar.gz','business.tar.gz.part','business.tar.gz']:
 p=r/name
 if p.exists(): out['files'][name]=p.stat().st_size
for name in ['background-export-result.json','background-images-result.json','business-export-result.json','business-receive-result.json','mysql-restore-result.json','business-staging-result.json','workspace-staging-result.json','infra-preparation-result.json','infra-start-result.json','queue-freeze-result.json','uploads-restore-result.json','minio-restore-result.json','elasticsearch-restore-result.json','vector-restore-result.json','vector-content-verification.json','upload-permissions-result.json','runtime-start-result.json','runtime-verification.json','app-start-result.json','app-auth-result.json','http-exposure-result.json']:
 p=r/name
 if p.exists():
  try:
   obj=json.loads(p.read_text())
   out['records'][name]={k:obj[k] for k in ['status','sha256','restored','targetPlatformStarted','laterSourceWritesIncluded','passed','loginPassed','businessAcceptanceComplete','publicAccessVerified'] if k in obj}
  except (ValueError,OSError): pass
raw=subprocess.check_output(['docker','ps','--format','{{json .}}'],text=True)
for line in raw.splitlines():
 obj=json.loads(line);out['containers'].append({k:obj[k] for k in ['Names','Status','Ports']})
for name in ['mcp-verification.json','docs-deployment-result.json','vector-persistence-verification.json']:
 p=r/name
 if p.exists():
  try:
   obj=json.loads(p.read_text());out['records'][name]={k:obj[k] for k in ['status','passed','backendUnchanged','allUserServicesVerified','restartPersistenceTested','collections','rows','filteredSearches'] if k in obj}
  except (ValueError,OSError): pass
for name in ['reconciliation-20261010/incremental-audit.json','reconciliation-20261010/field-differences.json','mcp-logging-20261010/result.json','mcp-logging-20261010/business-log-verification.json']:
 p=r/name
 if p.exists():
  try:
   obj=json.loads(p.read_text());out['records'][name]={k:obj[k] for k in ['status','equalTables','differentTables','incrementalApplied','laterSourceWritesApplied','backendEgressBlocked','schemaUnchanged','deploymentLogVerified','toolFailureLogVerified','fixturesRemoved'] if k in obj}
  except (ValueError,OSError): pass
print(json.dumps(out))
'''


def verified(source, target, source_key, target_key, good_source, good_target):
    a = source['records'].get(source_key, {})
    b = target['records'].get(target_key, {})
    return (a.get('status') == good_source and b.get('status') == good_target
            and bool(a.get('sha256')) and a.get('sha256') == b.get('sha256'))


def collect(password):
    import shlex
    clients = []
    try:
        samples = []
        for host in (m.SOURCE, m.TARGET):
            c = m.t.paramiko.SSHClient()
            c.set_missing_host_key_policy(m.Pinned())
            clients.append(c)
            c.connect(host, username='root', password=password, look_for_keys=False,
                      allow_agent=False, timeout=10, auth_timeout=10, banner_timeout=10)
            samples.append(json.loads(m.execute(c, 'python3 -c ' + shlex.quote(REMOTE_CHECK), timeout=20)))
        return samples
    finally:
        for c in clients:
            c.close()


def poll(password):
    previous = None
    while True:
        try:
            source, target = collect(password)
            now = time.time()
            files = target['files']
            count = files.get('background-images.tar.gz', files.get('background-images.tar.gz.part', 0))
            speed = None
            if previous and count >= previous[1]:
                speed = (count - previous[1]) / (time.monotonic() - previous[0])
            previous = (time.monotonic(), count)
            data = {
                'updated': now, 'error': None, 'source': m.SOURCE, 'target': m.TARGET,
                'imageBytes': count, 'bytesPerSecond': speed,
                'imageArchiveReceived': 'background-images.tar.gz' in files,
                'businessBytes': files.get('business.tar.gz', files.get('business.tar.gz.part', 0)),
                'imagesVerified': verified(source, target, 'background-export-result.json',
                    'background-images-result.json', 'IMAGE_STREAM_COMPLETE', 'IMAGES_STAGED'),
                'businessVerified': verified(source, target, 'business-export-result.json',
                    'business-receive-result.json', 'BUSINESS_STREAM_COMPLETE', 'BUSINESS_ARCHIVE_STAGED'),
                'databaseRestored': target['records'].get('mysql-restore-result.json', {}).get('status') == 'MYSQL_RESTORED',
                'records': target['records'], 'sourceRecords': source['records'],
                'containers': target['containers'],
            }
            with lock:
                state.clear()
                state.update(data)
        except Exception as exc:
            # Exception messages can include private server output. Publish only the type.
            with lock:
                state['error'] = type(exc).__name__
                state['failedAt'] = time.time()
        time.sleep(15)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/status':
            with lock:
                body = json.dumps(state).encode()
            kind = 'application/json; charset=utf-8'
        elif self.path == '/':
            body = PAGE.read_bytes()
            kind = 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=18108)
    args = parser.parse_args()
    password = os.environ.pop('SINGUX_SSH_PASSWORD', None) or getpass.getpass('SSH password: ')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=poll, args=(password,), daemon=True).start()
    print('Migration monitor: http://127.0.0.1:' + str(args.port), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
