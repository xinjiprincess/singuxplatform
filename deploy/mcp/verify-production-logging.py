"""Use normal owner APIs to prove deployment and tool failures reach the log query."""
import json
import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--migration', action='store_true')
    parser.add_argument('--retry-cleaned-failure', action='store_true')
    args = parser.parse_args()
    password = json.load(sys.stdin)['password']
    root = Path('/data/singux-mcp-logging-20261010-r1')
    if args.migration:
        assert socket.gethostname() == 'vm133'
        root = Path('/data/singux-migration-20261009/mcp-logging-20261010')
        container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
        assert container['Config']['Labels']['com.docker.compose.project.config_files'] == '/data/singux-migration-20261009/compose.app.test.json'
        assert set(container['NetworkSettings']['Networks']) == {'singux_default'}
        assert json.loads((root / 'result.json').read_text())['status'] == 'MIGRATION_MCP_LOGGING_UPDATED'
        previous = root / 'business-log-verification.json'
        if previous.exists():
            result = json.loads(previous.read_text())
            assert result['fixturesRemoved'], 'Clean prior fixtures before retry'
            if result.get('status') == 'MCP_FAILURE_LOGS_BUSINESS_VERIFIED':
                print(json.dumps(result))
                return
            assert args.retry_cleaned_failure, 'Explicit reviewed retry required'
            previous.rename(root / ('business-log-verification.failed-' + uuid.uuid4().hex + '.json'))
    token = ''

    def api(path, body=None):
        request = urllib.request.Request('http://127.0.0.1:8080' + path,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
        assert result.get('code') == '0000', 'Business API rejected ' + path + ' code=' + str(result.get('code'))
        return result.get('data')

    token = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})['token']
    password = None
    spaces = api('/api/space/list')
    assert isinstance(spaces, list) and spaces, 'No authorized owner space available'
    space = spaces[0]['id']
    created = []
    result = {'deploymentLogVerified': False, 'toolFailureLogVerified': False, 'fixturesRemoved': False}
    try:
        name = 'singux-log-test-' + uuid.uuid4().hex[:8]
        deployed = api('/api/mcp/create', {'spaceId': space, 'name': name + '-deploy',
            'description': 'Temporary deployment failure logging verification', 'installType': 'NPX', 'withDeploy': True,
            'mcpConfig': {'serverConfig': json.dumps({'mcpServers': {'failure': {'command': 'npx', 'args': ['-c', 'exit 1']}}})}})
        created.append(deployed['id'])
        for attempt in range(30):
            obj = api('/api/mcp/' + str(created[0]))
            if obj['deployStatus'] == 'DeployFailed': break
            time.sleep(4)
        assert obj['deployStatus'] == 'DeployFailed', 'Failure fixture did not finish deployment'
        component = api('/api/mcp/create', {'spaceId': space, 'name': name + '-tool',
            'description': 'Temporary unsuccessful tool logging verification', 'installType': 'COMPONENT', 'withDeploy': True,
            'mcpConfig': {'components': [], 'tools': [], 'prompts': [], 'resources': []}})
        created.append(component['id'])
        request_id = 'mcp-log-smoke-' + uuid.uuid4().hex
        output = api('/api/mcp/test', {'id': component['id'], 'requestId': request_id, 'executeType': 'TOOL',
                                      'name': 'missing-log-test-tool', 'params': {'password': 'dummy-log-redaction-test'}})
        assert output and output['success'] is False
        for attempt in range(30):
            records = {}
            for id in created:
                data = api('/api/requestLogs/list', {'current': 1, 'pageSize': 20,
                    'queryFilter': {'spaceId': space, 'targetType': 'Mcp', 'targetId': str(id), 'resultCode': '0001'}})
                records[id] = data.get('records', [])
            if all(records.values()): break
            time.sleep(3)
        assert all(records.values()), 'Failure logs missing from normal space log API'
        for row in records[created[0]]:
            assert row['requestId'].startswith('mcp:' + str(created[0]) + ':')
            assert row['from'] == 'McpDeploy'
        assert any(row['requestId'] == request_id for row in records[created[1]])
        assert 'dummy-log-redaction-test' not in json.dumps(records)
        result.update(deploymentLogVerified=True, toolFailureLogVerified=True,
                      fixtureIds=created.copy(), failedLogCounts=[len(records[id]) for id in created])
    finally:
        failures = []
        for id in created:
            try:
                api('/api/mcp/delete/' + str(id), {})
            except Exception:
                failures.append(id)
        result['fixturesRemoved'] = not failures
        result['cleanupPendingIds'] = failures
        (root / 'business-log-verification.json').write_text(json.dumps(result, indent=2))
    assert result['fixturesRemoved'], 'Temporary MCP fixture cleanup failed'
    result['status'] = 'MCP_FAILURE_LOGS_BUSINESS_VERIFIED'
    (root / 'business-log-verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
