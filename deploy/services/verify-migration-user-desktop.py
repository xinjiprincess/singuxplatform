"""Target-only authenticated desktop fixture; never executes an agent/model task."""
import base64
import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path('/data/singux-migration-20261009')


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retry-cleaned-failure', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    backend = json.loads(docker('inspect', 'singux-backend-1'))[0]
    assert backend['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.app.test.json')
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    assert json.loads(docker('network', 'inspect', 'singux_default'))[0]['Internal']
    output = ROOT / 'authenticated-desktop-verification.json'
    if output.exists():
        previous = json.loads(output.read_text())
        if previous['status'] == 'AUTHENTICATED_DESKTOP_VERIFIED':
            print(json.dumps(previous)); return
        assert args.retry_cleaned_failure and previous['fixturesRemoved'], 'Review prior fixture before retrying'
        output.rename(ROOT / ('authenticated-desktop-failed-' + uuid.uuid4().hex + '.json'))
    password = json.load(sys.stdin).pop('password')
    token = ''
    agent_id = conversation_id = runner = None
    runner_id = None
    stage = 'login'
    result = {'status': 'AUTHENTICATED_DESKTOP_TESTING', 'checks': [],
              'sourceChanged': False, 'modelInvoked': False, 'publicAccessVerified': False}

    def raw(path, data=None, authenticated=True):
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['Authorization'] = 'Bearer ' + token
        request = urllib.request.Request('http://127.0.0.1:8080' + path, headers=headers,
                    data=json.dumps(data).encode() if data is not None else None)
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()

    def api(path, data=None):
        record = json.loads(raw(path, data))
        assert record.get('code') == '0000', 'Business rejected: code=' + str(record.get('code'))
        return record.get('data')

    def save():
        output.write_text(json.dumps(result, indent=2))

    try:
        token = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})['token']
        password = None
        user = api('/api/user/getLoginInfo')
        assert isinstance(user.get('id'), int)
        runner = 'computer-agent-runner-' + str(user['id'])
        assert runner not in docker('ps', '-a', '--format', '{{.Names}}').splitlines(), 'Existing user desktop must not be replaced'
        result['fixtureRunnerName'] = runner
        spaces = [s for s in api('/api/space/list') if s.get('type') == 'Personal']
        assert len(spaces) == 1
        stage = 'agent-create'
        agent_id = api('/api/agent/add', {'spaceId': spaces[0]['id'],
                       'name': 'migration-desktop-' + uuid.uuid4().hex[:12],
                       'icon': '', 'description': 'Temporary migration desktop verification only'})
        assert isinstance(agent_id, int)
        result['fixtureAgentId'] = agent_id
        save()
        stage = 'conversation-create'
        conversation = api('/api/agent/conversation/create', {'agentId': agent_id, 'devMode': True})
        conversation_id = conversation['id']
        result['fixtureConversationId'] = conversation_id
        assert conversation['userId'] == user['id']
        save()
        stage = 'pod-ensure'
        api('/api/computer/pod/ensure?cId=' + str(conversation_id), {})
        runner_id = json.loads(docker('inspect', runner))[0]['Id']
        result['checks'].append('authenticated-pod-ensure')
        stage = 'pod-ready'
        for attempt in range(40):
            status = api('/api/computer/pod/vnc-status?cId=' + str(conversation_id))
            result['lastVncStatus'] = {k: status.get(k) for k in ('vnc_ready', 'novnc_ready')}
            result['vncResponseKeys'] = sorted(status.keys())
            save()
            if status.get('vnc_ready') and status.get('novnc_ready'):
                break
            time.sleep(2)
        else:
            raise RuntimeError('Desktop did not become ready')
        config = json.loads(docker('inspect', runner))[0]
        runner_id = config['Id']
        assert not config['HostConfig']['Privileged'] and not config['HostConfig']['PortBindings']
        assert config['HostConfig']['Memory'] == 1610612736
        assert set(config['NetworkSettings']['Networks']) == {'singux-execution'}
        result['checks'].append('authenticated-vnc-ready-and-private-limits')
        stage = 'desktop-html'
        path = '/computer/desktop/' + str(conversation_id) + '/'
        assert b'noVNC' in raw(path + 'vnc.html')
        result['checks'].append('authenticated-frontend-desktop-html')
        stage = 'unauthenticated-denied'
        try:
            raw(path + 'vnc.html', authenticated=False)
            raise AssertionError('Anonymous desktop access accepted')
        except urllib.error.HTTPError as error:
            assert error.code in (401, 403)
        result['checks'].append('anonymous-desktop-denied')
        stage = 'websocket'
        with socket.create_connection(('127.0.0.1', 8080), timeout=30) as stream:
            key = base64.b64encode(os.urandom(16)).decode()
            request = ('GET ' + path + 'websockify HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n'
                       'Connection: Upgrade\r\nSec-WebSocket-Key: ' + key + '\r\n'
                       'Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n'
                       'Authorization: Bearer ' + token + '\r\n\r\n')
            stream.sendall(request.encode())
            answer = b''
            while b'\r\n\r\n' not in answer and len(answer) < 16384:
                chunk = stream.recv(4096)
                if not chunk:
                    break
                answer += chunk
            assert answer.startswith(b'HTTP/1.1 101'), 'Authenticated desktop WebSocket rejected'
        result['checks'].append('authenticated-frontend-websocket-upgrade')
        api('/api/computer/pod/keepalive?cId=' + str(conversation_id), {})
        result['checks'].append('authenticated-keepalive')
        result['status'] = 'AUTHENTICATED_DESKTOP_VERIFIED'
    except Exception as error:
        result.update(status='AUTHENTICATED_DESKTOP_FAILED', failureStage=stage,
                      errorType=type(error).__name__)
    finally:
        errors = []
        if runner and runner in docker('ps', '-a', '--format', '{{.Names}}').splitlines() and conversation_id:
            # This name was absent before ensure; never touch another user's runner.
            try:
                config = json.loads(docker('inspect', runner))[0]
                if runner_id:
                    assert config['Id'] == runner_id
                subprocess.run(['docker', 'stop', '--time', '20', runner], capture_output=True, timeout=60)
                if runner in docker('ps', '-a', '--format', '{{.Names}}').splitlines():
                    docker('rm', runner)
            except Exception:
                if runner in docker('ps', '-a', '--format', '{{.Names}}').splitlines():
                    errors.append('fixture-runner')
        if conversation_id:
            try:
                api('/api/agent/conversation/delete/' + str(conversation_id), {})
            except Exception:
                errors.append('fixture-conversation')
        if agent_id:
            try:
                api('/api/agent/delete/' + str(agent_id), {})
            except Exception:
                errors.append('fixture-agent')
        result['fixturesRemoved'] = not errors
        result['cleanupErrors'] = errors
        result['fixtureDirectoriesRetained'] = True
        if errors:
            result['status'] = 'AUTHENTICATED_DESKTOP_FAILED'
        result['completedUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(json.dumps(result))


if __name__ == '__main__':
    main()
