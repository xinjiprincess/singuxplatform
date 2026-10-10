"""Connect the existing local preview without changing its image or data mounts."""
import json
import subprocess
import time


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def main():
    name = 'singux-local-backend-1'
    network = 'singux-local_default'
    previous = name + '-before-services'
    config = json.loads(docker('inspect', name))[0]
    host = config['HostConfig']
    if set(config['NetworkSettings']['Networks']) != {network} or host['PortBindings']:
        raise RuntimeError('Unexpected local backend network/ports; inspect manually')
    if host.get('Privileged') or host.get('Devices') or host.get('CapAdd'):
        raise RuntimeError('Unexpected privileged configuration')
    mcp = 'singux-services-local-mcp-proxy-1'
    mcp_info = json.loads(docker('inspect', mcp))[0]
    if network not in mcp_info['NetworkSettings']['Networks']:
        docker('network', 'connect', '--alias', 'singux-mcp', network, mcp)
    replacement = {
        'BUILD_SERVER_URL': 'http://singux-file-service:60000/api',
        'AI_AGENT_URL': 'http://singux-rcoder:8090',
        'DOCKER_PROXY_URL': 'http://singux-rcoder:8088',
        'MCP_PROXY_URL': 'http://singux-mcp:8080',
        'CODE_EXECUTE_URL': 'http://singux-mcp:8080/api/run_code_with_log',
    }
    current_env = dict(value.split('=', 1) for value in config['Config']['Env'])
    if all(current_env.get(key) == value for key, value in replacement.items()):
        if config['State'].get('Health', {}).get('Status') != 'healthy':
            raise RuntimeError('Already configured backend is not healthy')
        print('LOCAL_BACKEND_ALREADY_CONNECTED')
        return
    existing = docker('ps', '-a', '--format', '{{.Names}}').splitlines()
    if previous in existing:
        raise RuntimeError('Rollback container already exists; do not overwrite it')
    args = ['create', '--name', name, '--network', network, '--network-alias', 'backend',
            '--restart', host['RestartPolicy']['Name']]
    for value in config['Config']['Env']:
        key = value.split('=', 1)[0]
        if key not in replacement:
            args.extend(['--env', value])
    for key, value in replacement.items():
        args.extend(['--env', key + '=' + value])
    for mount in config['Mounts']:
        if mount['Type'] not in ('volume', 'bind'):
            raise RuntimeError('Unsupported mount type')
        source = mount.get('Name') if mount['Type'] == 'volume' else mount['Source']
        spec = source + ':' + mount['Destination'] + (':ro' if not mount['RW'] else '')
        args.extend(['--volume', spec])
    for value in host.get('ExtraHosts') or []:
        args.extend(['--add-host', value])
    for key, value in (config['Config'].get('Labels') or {}).items():
        args.extend(['--label', key + '=' + value])
    for key, flag in [('Memory', '--memory'), ('MemorySwap', '--memory-swap'), ('PidsLimit', '--pids-limit')]:
        if host.get(key):
            args.extend([flag, str(host[key])])
    if host.get('NanoCpus'):
        args.extend(['--cpus', str(host['NanoCpus'] / 1e9)])
    entry = config['Config'].get('Entrypoint') or []
    if entry:
        args.extend(['--entrypoint', entry[0]])
    args.append(config['Image'])
    args.extend(entry[1:])
    args.extend(config['Config'].get('Cmd') or [])
    docker('stop', name)
    docker('rename', name, previous)
    docker('network', 'disconnect', network, previous)
    try:
        docker(*args)
        docker('start', name)
        for _ in range(90):
            current = json.loads(docker('inspect', name))[0]
            if current['State'].get('Health', {}).get('Status') == 'healthy':
                if [(m['Source'], m['Destination']) for m in current['Mounts']] != [(m['Source'], m['Destination']) for m in config['Mounts']]:
                    raise RuntimeError('Mount mismatch')
                print('LOCAL_BACKEND_CONNECTED; same image and mounts; rollback=' + previous)
                return
            if not current['State']['Running']:
                raise RuntimeError('Backend exited')
            time.sleep(3)
        raise RuntimeError('Backend health timeout')
    except Exception:
        if name in docker('ps', '-a', '--format', '{{.Names}}').splitlines():
            docker('rm', '-f', name)
        docker('rename', previous, name)
        docker('network', 'connect', '--alias', 'backend', network, name)
        docker('start', name)
        raise


if __name__ == '__main__':
    main()
