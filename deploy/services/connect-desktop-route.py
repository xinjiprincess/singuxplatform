"""Add only the authenticated backend desktop proxy to the existing frontend template."""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
TEMPLATE = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64/default-model-proxy.conf.template')
ROUTE = '''    location ^~ /computer/ {
        proxy_pass http://backend:18085;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

'''


def run(args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def main():
    result = json.loads((HERE / 'deployment-result.json').read_text())
    if result['status'] != 'PLATFORM_CONNECTED':
        raise RuntimeError('Backend not connected')
    backup = Path(result['backup'])
    original = TEMPLATE.read_text()
    if '/computer/' in original or original.count('    location /api/ {') != 1:
        raise RuntimeError('Unexpected frontend template; review required')
    config = json.loads(run(['docker', 'inspect', 'singux-frontend-1']))[0]
    expected = [m for m in config['Mounts'] if m['Destination'] == '/etc/nginx/templates/default.conf.template']
    assert len(expected) == 1 and expected[0]['Source'] == str(TEMPLATE)
    old_rendered = run(['docker', 'exec', 'singux-frontend-1', 'cat', '/etc/nginx/conf.d/default.conf'])
    (backup / 'frontend-template.before').write_text(original)
    (backup / 'frontend-config.before').write_bytes(old_rendered)
    updated = original.replace('    location /api/ {', ROUTE + '    location /api/ {')
    env = dict(value.split('=', 1) for value in config['Config']['Env'])
    rendered = updated
    for key in ['SERVER_NAME', 'API_UPSTREAM', 'MODEL_PROXY_UPSTREAM', 'URI_NAME']:
        if key not in env:
            raise RuntimeError('Missing frontend environment ' + key)
        rendered = rendered.replace('${' + key + '}', env[key])
    if '${' in rendered:
        raise RuntimeError('Unresolved template variable')
    candidate = HERE / 'frontend-runtime.conf'
    candidate.write_text(rendered)
    try:
        run(['docker', 'cp', str(candidate), 'singux-frontend-1:/etc/nginx/conf.d/default.conf'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-t'])
        # Keep the bind-mounted inode so the running container sees the persistent update.
        TEMPLATE.write_text(updated)
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        result['desktopRouteConnected'] = True
        (HERE / 'deployment-result.json').write_text(json.dumps(result, indent=2))
        print('DESKTOP_AUTHENTICATED_PROXY_CONNECTED')
    except BaseException:
        TEMPLATE.write_text(original)
        run(['docker', 'cp', str(backup / 'frontend-config.before'), 'singux-frontend-1:/etc/nginx/conf.d/default.conf'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        raise


if __name__ == '__main__':
    main()
