"""Move exhausted MCP tmpfs caches to dedicated Docker volumes; preserve original caches."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    assert p.returncode == 0, 'MCP cache operation failed: ' + ' '.join(args[:3])
    return p.stdout


def main():
    os.umask(0o077)
    root = Path('/data/singux-mcp-cache-repair-20261010')
    assert not root.exists(), 'Preserve original cache backup'
    assert shutil.disk_usage('/data').free > 3 * 1024**3
    proxy = json.loads(run(['docker', 'inspect', 'singux-mcp-proxy-1']))[0]
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id']
    expected = json.loads(run(['docker', 'image', 'inspect', 'singux/mcp-proxy:0.2.8-20261009-recovery-r1']))[0]['Id']
    assert proxy['Image'] == expected
    assert proxy['Config']['User'] == '10001:10001'
    assert proxy['HostConfig']['ReadonlyRootfs']
    labels = proxy['Config']['Labels']
    files = labels['com.docker.compose.project.config_files'].split(',')
    path = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64/compose.mcp.json')
    assert files[-1] == str(path)
    original = path.read_text()
    config = json.loads(original)
    service = config['services']['mcp-proxy']
    assert not service.get('volumes')
    root.mkdir(mode=0o700)
    (root / 'compose.before.json').write_text(original)
    (root / 'container.before.json').write_text(json.dumps(proxy, indent=2))
    run(['docker', 'cp', 'singux-mcp-proxy-1:/home/mcp', str(root / 'home.before')])
    run(['docker', 'cp', 'singux-mcp-proxy-1:/tmp', str(root / 'tmp.before')])
    volumes = {'singux_mcp-home-cache': '/home/mcp', 'singux_mcp-tmp-cache': '/tmp'}
    helper = 'singux-mcp-cache-init-20261010'
    for name in volumes:
        exists = subprocess.run(['docker', 'volume', 'inspect', name], capture_output=True).returncode == 0
        assert not exists, 'Do not reuse an unknown volume'
        run(['docker', 'volume', 'create', '--label', 'singux.purpose=mcp-cache', name])
    args = ['docker', 'run', '--rm', '--name', helper, '--network', 'none', '--user', '0:0',
            '--read-only', '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL', '--cap-add', 'CHOWN']
    for name, dest in volumes.items(): args += ['--mount', 'type=volume,src=' + name + ',dst=' + dest]
    # The helper can access only these newly created, dedicated cache volumes.
    run(args + ['--entrypoint', 'chown', proxy['Config']['Image'], '-R', '10001:10001', '/home/mcp', '/tmp'])
    tmpfs = service['tmpfs']
    assert isinstance(tmpfs, list)
    service['tmpfs'] = [item for item in tmpfs if item.split(':', 1)[0] not in ['/home/mcp', '/tmp']]
    assert len(tmpfs) - len(service['tmpfs']) == 2
    service['volumes'] = [name + ':' + dest for name, dest in volumes.items()]
    for name in volumes:
        config.setdefault('volumes', {})[name] = {'external': True, 'name': name}
    cmd = ['docker', 'compose', '-p', 'singux', '--project-directory', str(path.parent),
           '--env-file', str(path.parent / '.env')]
    for file in files: cmd += ['-f', file]
    try:
        path.write_text(json.dumps(config, indent=2))
        run(cmd + ['config', '--quiet'])
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', '--wait', '--wait-timeout', '90', 'mcp-proxy'])
        run(['docker', 'exec', 'singux-backend-1', 'curl', '-fsS', '--max-time', '10', 'http://mcp-proxy:8080/health'])
        after = json.loads(run(['docker', 'inspect', 'singux-mcp-proxy-1']))[0]
        assert after['HostConfig']['ReadonlyRootfs']
        assert after['HostConfig']['Memory'] == proxy['HostConfig']['Memory']
        assert {m['Name']: m['Destination'] for m in after['Mounts']} == volumes
        assert json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id'] == backend
    except BaseException:
        path.write_text(original)
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'mcp-proxy'])
        raise
    result = {'status': 'MCP_CACHE_VOLUMES_READY', 'backendUnchanged': True,
              'readonlyRootPreserved': True, 'memoryLimitPreserved': True,
              'oldCachesBackedUp': True, 'volumes': list(volumes), 'userConfigsChanged': False}
    (root / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
