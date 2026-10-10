"""Route only the production documentation locations to bundled frontend assets."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, 'Gateway validation or reload failed'


def main():
    path = Path('/etc/nginx/snippets/singu-download-site.conf')
    backup = Path('/data/singux-docs-20261010/release/gateway.before.conf')
    original = path.read_text()
    assert not backup.exists(), 'Preserve gateway backup'
    changed = original
    for location in ['location = /docs {', 'location ^~ /docs/ {']:
        assert changed.count(location) == 1
        start = changed.index(location)
        end = changed.index('}', start) + 1
        block = changed[start:end]
        assert block.count('proxy_pass http://127.0.0.1:18764;') == 1
        replacement = block.replace('proxy_pass http://127.0.0.1:18764;',
                                    'proxy_pass http://127.0.0.1:8080;\n'
                                    '    add_header X-Frame-Options SAMEORIGIN always;\n'
                                    '    add_header Content-Security-Policy "frame-ancestors \'self\'" always;')
        changed = changed[:start] + replacement + changed[end:]
    backup.write_text(original)
    backup.chmod(0o600)
    try:
        path.write_text(changed)
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
        with urllib.request.urlopen('https://www.ciyuancenter.cc/docs/', timeout=30) as response:
            content = response.read()
            assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
        with urllib.request.urlopen('http://127.0.0.1:8080/docs/', timeout=30) as response:
            assert response.read() == content, 'Public docs differ from bundled assets'
        record = {'status': 'PUBLIC_DOCS_ROUTED', 'url': 'https://www.ciyuancenter.cc/docs/',
                  'sha256': hashlib.sha256(content).hexdigest(), 'framePolicy': 'SAMEORIGIN',
                  'downloadRoutesChanged': False}
        Path('/data/singux-docs-20261010/gateway-result.json').write_text(json.dumps(record, indent=2))
        print(json.dumps(record))
    except BaseException:
        path.write_text(original)
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
        raise


if __name__ == '__main__':
    main()
