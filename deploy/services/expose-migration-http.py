"""Add standard HTTP to the already running target test frontend only."""
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/data/singux-migration-20261009')


def main():
    os.umask(0o077)
    assert json.loads((ROOT / 'app-start-result.json').read_text())['status'] == 'APP_HTTP_READY'
    path = ROOT / 'compose.app.test.json'
    original = path.read_text()
    config = json.loads(original)
    ports = config['services']['frontend']['ports']
    assert ports in [['8080:80'], ['80:80', '8080:80']]
    if ports == ['8080:80']:
        backup = ROOT / 'compose.app.before-http.json'
        assert not backup.exists()
        backup.write_text(original)
        config['services']['frontend']['ports'] = ['80:80', '8080:80']
        path.write_text(json.dumps(config, indent=2))
    cmd = ['docker', 'compose', '-p', 'singux', '-f', str(path)]
    for args in [['config', '--quiet'], ['up', '-d', '--no-deps', '--pull', 'never', 'frontend']]:
        p = subprocess.run(cmd + args, capture_output=True)
        assert p.returncode == 0, 'Frontend HTTP configuration failed; preserve backup'
    with urllib.request.urlopen('http://127.0.0.1/login', timeout=20) as r:
        assert r.status == 200
    result = {'status': 'TARGET_HTTP_BOUND', 'ports': [80, 8080], 'sourceChanged': False,
              'dnsChanged': False, 'publicAccessVerified': False}
    (ROOT / 'http-exposure-result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
