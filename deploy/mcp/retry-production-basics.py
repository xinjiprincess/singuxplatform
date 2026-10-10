"""Retry two existing basic services only through normal administrator APIs."""
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


def main():
    os.umask(0o077)
    password = json.load(sys.stdin).pop('password')
    root = Path('/data/singux-mcp-state-repair-20261010')
    token = ''

    def api(path, body=None):
        q = urllib.request.Request('http://127.0.0.1:8080' + path,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(q, timeout=45) as r:
                result = json.load(r)
        except urllib.error.HTTPError as e:
            return None, 'HTTP_' + str(e.code)
        return (result.get('data'), None) if result.get('code') == '0000' else (None, result.get('code'))

    login, error = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})
    password = None
    assert login and login.get('token'), 'Administrator login rejected'
    token = login['token']
    results = []
    for id, package in [(1, 'mcp-server-fetch'), (6, 'mcp-server-time')]:
        obj, error = api('/api/mcp/' + str(id))
        if error:
            results.append({'id': id, 'status': 'NOT_AUTHORIZED_OR_UNAVAILABLE', 'code': error})
            continue
        cfg = obj['mcpConfig']['serverConfig']
        if isinstance(cfg, str): cfg = json.loads(cfg)
        servers = cfg.get('mcpServers', {})
        assert len(servers) == 1
        server = next(iter(servers.values()))
        assert server['command'] == 'uvx' and server['args'] == [package]
        backup = root / ('retry-' + str(id) + '.before.json')
        assert not backup.exists(), 'Preserve prior retry backup'
        backup.write_text(json.dumps(obj, ensure_ascii=False))
        body = {key: obj[key] for key in ['id', 'name', 'description', 'icon', 'mcpConfig'] if key in obj}
        body['withDeploy'] = True
        _, error = api('/api/mcp/update', body)
        results.append({'id': id, 'status': 'RETRY_QUEUED' if not error else 'RETRY_REJECTED', 'code': error})
    for attempt in range(18):
        pending = False
        for result in results:
            if result['status'] not in ['RETRY_QUEUED', 'Deploying']: continue
            obj, error = api('/api/mcp/' + str(result['id']))
            if error: continue
            result['status'] = obj['deployStatus']
            pending |= result['status'] == 'Deploying'
        if not pending: break
        time.sleep(5)
    record = {'status': 'MCP_BASIC_RETRY_CHECKED', 'services': results, 'configsChanged': False,
              'permissionsBypassed': False, 'allUserServicesVerified': False}
    (root / 'retry-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
