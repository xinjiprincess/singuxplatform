"""Target-only model contract test using an internal, synthetic OpenAI fixture."""
import datetime
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid

ROOT = Path('/data/singux-migration-20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retry-cleaned-failure', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    backend = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
    assert backend['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.app.test.json')
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal']
    gateway = network['IPAM']['Config'][0]['Gateway']
    assert ipaddress.ip_address(gateway).is_private
    destination = ROOT / 'model-contract-verification.json'
    if destination.exists():
        previous = json.loads(destination.read_text())
        if previous['status'] == 'MODEL_CONTRACT_VERIFIED':
            print(json.dumps(previous))
            return
        assert args.retry_cleaned_failure and previous['fixturesRemoved'] and previous['fixtureListenerStopped'], 'Review prior contract test before rerunning'
        destination.rename(ROOT / ('model-contract-failed-' + uuid.uuid4().hex + '.json'))
    password = json.load(sys.stdin)['password']
    marker = 'singux-contract-' + uuid.uuid4().hex[:12]
    expected = 'fixture-' + uuid.uuid4().hex
    answer = 'SinguX \u5185\u7f51\u6d4b\u8bd5\u901a\u8fc7'
    observed = []
    attempts = []
    token = ''
    access_key = None
    model_id = None
    stage = 'fixture-start'
    result = {'status': 'MODEL_CONTRACT_TESTING', 'syntheticUpstream': True,
              'realProviderVerified': False, 'backendEgressBlocked': True,
              'sourceChanged': False, 'dnsChanged': False, 'checks': {}}

    class Fixture(BaseHTTPRequestHandler):
        def do_POST(self):
            attempts.append({'pathMatched': self.path == '/v1/chat/completions',
                             'authorizationMatched': self.headers.get('Authorization') == 'Bearer ' + expected})
            if self.path != '/v1/chat/completions' or self.headers.get('Authorization') != 'Bearer ' + expected:
                self.send_error(403)
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                self.send_error(400)
                return
            body = json.loads(self.rfile.read(length))
            if body.get('model') != marker:
                self.send_error(400)
                return
            observed.append({'stream': bool(body.get('stream')), 'modelMatched': True})
            common = {'id': 'chatcmpl-fixture', 'created': 1791619200, 'model': marker}
            usage = {'prompt_tokens': 3, 'completion_tokens': 6, 'total_tokens': 9}
            if body.get('stream'):
                chunks = [dict(common, object='chat.completion.chunk', choices=[
                    {'index': 0, 'delta': {'role': 'assistant', 'content': answer}, 'finish_reason': None}]),
                    dict(common, object='chat.completion.chunk', choices=[
                    {'index': 0, 'delta': {}, 'finish_reason': 'stop'}], usage=usage)]
                data = (''.join('data: ' + json.dumps(c, ensure_ascii=False) + '\n\n' for c in chunks)
                        + 'data: [DONE]\n\n').encode()
                kind = 'text/event-stream; charset=utf-8'
            else:
                data = json.dumps(dict(common, object='chat.completion', choices=[
                    {'index': 0, 'message': {'role': 'assistant', 'content': answer}, 'finish_reason': 'stop'}],
                    usage=usage), ensure_ascii=False).encode()
                kind = 'application/json; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((gateway, 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def api(path, body=None):
        request = urllib.request.Request('http://127.0.0.1:8080' + path,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                record = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError('Business HTTP rejected code=' + str(exc.code)) from None
        if record.get('code') != '0000':
            diagnostic = str(record.get('message', ''))
            for secret in (token, access_key, expected, password):
                if secret:
                    diagnostic = diagnostic.replace(secret, '[REDACTED]')
            diagnostic = re.sub(r'https?://[^\s"<>]+', '[URL]', diagnostic)
            diagnostic = re.sub(r'(?i)bearer\s+\S+|(?:ak|sk)-[A-Za-z0-9_-]+', '[REDACTED]', diagnostic)
            result['businessError'] = {'code': str(record.get('code')), 'message': diagnostic[:400]}
            raise AssertionError('Business API rejected')
        return record.get('data')

    def proxy(key, stream):
        request = urllib.request.Request('http://127.0.0.1:8080/api/proxy/model/' + str(model_id) + '/v1/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
            data=json.dumps({'model': marker, 'messages': [{'role': 'user', 'content': 'fixture-only'}],
                             'stream': stream, 'max_tokens': 16}).encode())
        with urllib.request.urlopen(request, timeout=45) as response:
            assert response.status == 200
            return response.read().decode()

    try:
        stage = 'login'
        token = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})['token']
        password = None
        spaces = api('/api/space/list')
        personal = [space for space in spaces if space.get('type') == 'Personal']
        assert len(personal) == 1, 'Expected one authorized personal space'
        space_id = personal[0]['id']
        definition = {'spaceId': space_id, 'name': marker, 'description': 'Temporary synthetic internal model contract test',
                      'model': marker, 'type': 'Chat', 'types': ['Text'], 'apiProtocol': 'OpenAI',
                      'strategy': 'RoundRobin', 'apiInfoList': [{'url': 'http://' + gateway + ':' + str(server.server_port) + '/v1',
                      'key': expected, 'weight': 1}], 'maxTokens': 16, 'maxContextTokens': 4096,
                      'functionCall': 'Unsupported', 'isReasonModel': 0, 'enabled': 1,
                      'accessControl': 0, 'usageScenarios': ['OpenApi', 'Workflow', 'ChatBot']}
        stage = 'stream-connectivity'
        connectivity = api('/api/model/test-connectivity', definition)
        assert connectivity in (True, None), 'Unexpected successful connectivity response'
        assert observed and observed[-1]['stream'], 'Connectivity did not reach the fixture'
        result['checks']['connectivitySseParsed'] = True
        stage = 'create-model'
        api('/api/model/save', definition)
        models = api('/api/model/list/space/' + str(space_id), {})
        selected = [m for m in models if m['name'] == marker]
        assert len(selected) == 1
        model_id = selected[0]['id']
        result['fixtureModelId'] = model_id
        stage = 'create-key'
        expire = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)).isoformat()
        key = api('/api/user/api-key/create', {'name': marker, 'expire': expire})
        access_key = key['accessKey']
        api('/api/user/api-key/update', {'accessKey': access_key, 'status': 1, 'expire': expire,
                                       'apiConfigs': [], 'modelIds': [model_id]})
        stage = 'reject-invalid-key'
        before = len(observed)
        try:
            proxy('invalid-fixture-key', False)
            raise AssertionError('Invalid key unexpectedly accepted')
        except urllib.error.HTTPError as exc:
            assert exc.code in (401, 403)
        assert len(observed) == before
        result['checks']['invalidKeyRejectedBeforeUpstream'] = True
        stage = 'proxy-json'
        response = json.loads(proxy(access_key, False))
        assert response['choices'][0]['message']['content'] == answer
        assert response['usage']['total_tokens'] == 9
        result['checks']['authorizedJsonContentAndUsage'] = True
        stage = 'proxy-stream'
        response = proxy(access_key, True)
        chunks = [json.loads(line[6:]) for line in response.splitlines()
                  if line.startswith('data: ') and line != 'data: [DONE]']
        assert 'data: [DONE]' in response
        text = ''.join(choice.get('delta', {}).get('content', '') for chunk in chunks for choice in chunk.get('choices', []))
        assert text == answer
        result['checks']['authorizedSseChineseContent'] = True
        assert len(observed) == 3 and all(item['modelMatched'] for item in observed)
        result['checks']['privateFixtureOnly'] = True
        result['status'] = 'MODEL_CONTRACT_VERIFIED'
    except Exception as exc:
        result.update(status='MODEL_CONTRACT_FAILED', failedStage=stage, errorType=type(exc).__name__,
                      fixtureAttempts=attempts, successfulFixtureCalls=len(observed))
    finally:
        cleanup = []
        if access_key:
            try:
                api('/api/user/api-key/delete/' + access_key, {})
            except Exception:
                cleanup.append('temporary-key-revocation')
        if model_id is not None:
            try:
                api('/api/model/' + str(model_id) + '/delete')
            except Exception:
                cleanup.append('temporary-model-deletion')
        elif stage == 'create-model':
            cleanup.append('check-temporary-model-name:' + marker)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        result.update(fixturesRemoved=not cleanup, cleanupPending=cleanup, fixtureListenerStopped=not thread.is_alive(),
                      completedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if cleanup:
            result['status'] = 'MODEL_CONTRACT_CLEANUP_REQUIRED'
        destination.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    assert result['status'] == 'MODEL_CONTRACT_VERIFIED', 'Model contract not verified; inspect sanitized report'


if __name__ == '__main__':
    main()
