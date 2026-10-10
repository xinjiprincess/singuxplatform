"""Create disposable service fixtures and check storage, desktop handshake and limits."""
import base64
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = 'singux-production-check-20261009'
DESKTOP_PROJECT = 'singux-production-desktop-project-20261009'
USER = 'singux-production-desktop-check-20261009'


def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True, text=True).stdout.strip()


def remove_fixture(name):
    if name not in docker('ps', '-a', '--format', '{{.Names}}').splitlines():
        return
    docker('stop', name)
    # RCoder containers can be AutoRemove; stopping already removes them.
    for _ in range(30):
        if name not in docker('ps', '-a', '--format', '{{.Names}}').splitlines():
            return
        subprocess.run(['docker', 'rm', name], capture_output=True)
        time.sleep(1)
    raise RuntimeError('Fixture removal did not complete: ' + name)


def request(port, path, body=None):
    headers = {'Content-Type': 'application/json', 'x-api-key': (HERE / 'service-key').read_text()}
    req = urllib.request.Request('http://127.0.0.1:' + str(port) + path, headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=240) as response:
        value = json.load(response)
    if value.get('success') is False:
        raise RuntimeError('Service rejected fixture')
    return value


def main():
    checks = []
    try:
        urllib.request.urlopen('http://127.0.0.1:18096/computer/pod/list', timeout=20)
        raise RuntimeError('Unauthenticated control request accepted')
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403):
            raise
        checks.append('unauthenticated-control-denied')
    names = ['web-agent-runner-' + PROJECT, 'computer-agent-runner-' + USER]
    existing = docker('ps', '-a', '--format', '{{.Names}}').splitlines()
    if any(name in existing for name in names):
        raise RuntimeError('Fixture containers already exist; review instead of overwrite')
    created = []
    try:
        try:
            request(16000, '/api/project/create-project', {'projectId': PROJECT, 'templateType': 'react'})
        except urllib.error.HTTPError as error:
            body = error.read().decode()
            if 'already exists' not in body:
                raise
        request(18096, '/computer/pod/ensure', {'user_id': USER, 'project_id': PROJECT,
            'service_type': 'web-agent-runner'})
        created.append(names[0])
        docker('exec', names[0], 'test', '-f', '/app/project_workspace/' + PROJECT + '/package.json')
        checks.append('template-and-runner-shared-files')
        remove_fixture(names[0])
        created.remove(names[0])
        request(18096, '/computer/pod/ensure', {'user_id': USER, 'project_id': DESKTOP_PROJECT,
            'service_type': 'computer-agent-runner'})
        created.append(names[1])
        config = json.loads(docker('inspect', names[1]))[0]
        host = config['HostConfig']
        assert not host['Privileged'] and host['Memory'] == 1610612736
        assert host['MemorySwap'] == 3221225472 and host['PidsLimit'] == 256
        assert not host['PortBindings']
        assert set(config['NetworkSettings']['Networks']) == {'singux-execution'}
        assert all('docker.sock' not in mount['Destination'] for mount in config['Mounts'])
        checks.append('desktop-memory-swap-pids-network-limits')
        base = '/computer/vnc/' + USER + '/' + DESKTOP_PROJECT + '/'
        for attempt in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:18088' + base + 'vnc.html', timeout=20) as response:
                    assert b'noVNC' in response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code not in (502, 503) or attempt == 29:
                    raise
                time.sleep(2)
        checks.append('desktop-html-through-private-gateway')
        with socket.create_connection(('127.0.0.1', 18088), timeout=60) as stream:
            key = base64.b64encode(b'0123456789abcdef').decode()
            headers = 'GET ' + base + 'websockify HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key + '\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n\r\n'
            stream.sendall(headers.encode())
            answer = b''
            while b'\r\n\r\n' not in answer and len(answer) < 16384:
                chunk = stream.recv(4096)
                if not chunk:
                    break
                answer += chunk
            assert answer.startswith(b'HTTP/1.1 101'), answer[:80]
            checks.append('desktop-websocket-upgrade')
        result = {'passed': True, 'checks': checks, 'realModelTested': False,
                  'publicUserDesktopTested': False, 'fixtureDirectoriesRetained': [PROJECT, USER],
                  'desktopProject': DESKTOP_PROJECT}
        (HERE / 'runtime-verification.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    finally:
        for name in created:
            remove_fixture(name)


if __name__ == '__main__':
    main()
