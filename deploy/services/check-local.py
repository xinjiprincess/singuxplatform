"""Read-only local infrastructure checks; does not invoke paid models."""
import json
import urllib.request
from pathlib import Path
import subprocess


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    checks = []
    for name, endpoint in [('file-server', 'http://127.0.0.1:16000/health'),
                           ('rcoder', 'http://127.0.0.1:8086/health')]:
        with urllib.request.urlopen(endpoint, timeout=15) as response:
            assert response.status == 200
        checks.append(name + ':health')
    backend = json.loads(docker('inspect', 'singux-local-backend-1'))[0]
    assert backend['State']['Health']['Status'] == 'healthy'
    for host, port in [('singux-file-service', 60000), ('singux-rcoder', 8090), ('singux-mcp', 8080)]:
        docker('exec', 'singux-local-backend-1', 'curl', '-fsS', f'http://{host}:{port}/health')
        checks.append('backend:dns:' + host)
    project = 'singux-service-check-20261009'
    docker('exec', 'singux-services-local-file-server-1', 'test', '-f', f'/data/projects/{project}/package.json')
    docker('exec', 'web-agent-runner-' + project, 'test', '-f', f'/app/project_workspace/{project}/package.json')
    checks.append('file-server:runner:shared-project')
    docker('exec', 'web-agent-runner-singux-isolated-check', 'test', '-f', '/app/project_workspace/1/1/singux-isolated-check/package.json')
    checks.append('tenant-space-project:shared-path')
    for name in ['web-agent-runner-' + project, 'computer-agent-runner-singux-local-desktop-check']:
        config = json.loads(docker('inspect', name))[0]
        assert config['State']['Running'] and not config['HostConfig']['Privileged']
        assert config['HostConfig']['Memory'] > 0
        assert all('docker.sock' not in m['Destination'] for m in config['Mounts'])
        checks.append(name + ':bounded:no-docker-socket')
    with urllib.request.urlopen('http://127.0.0.1:18088/computer/vnc/singux-local-desktop-check/singux-desktop-check/vnc.html', timeout=15) as response:
        assert b'noVNC' in response.read()
    checks.append('gateway:vnc-route')
    with urllib.request.urlopen('http://127.0.0.1:18088/proxy/4000/', timeout=15) as response:
        assert b'@vite/client' in response.read()
    checks.append('gateway:vite-route')
    output = Path(__file__).resolve().parents[2] / 'outputs/services-local-check-20261009.json'
    output.write_text(json.dumps({'passed': True, 'checks': checks, 'realModelTested': False,
        'productionApproved': False}, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'checks': len(checks), 'record': str(output)}))


if __name__ == '__main__':
    main()
