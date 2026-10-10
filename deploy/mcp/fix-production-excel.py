"""Validate a pinned direct Excel package before replacing its broken hub launcher."""
import copy
import json
import os
from pathlib import Path
import subprocess
import time


def sql(query):
    p = subprocess.run(['docker', 'exec', '-i', 'singux-mysql-1', 'sh', '-c',
        'exec mysql --default-character-set=utf8mb4 -uroot --password="$MYSQL_ROOT_PASSWORD" -B -N --raw'],
        input=query, capture_output=True, text=True)
    assert p.returncode == 0, 'Excel configuration query rejected'
    return p.stdout


def main():
    os.umask(0o077)
    root = Path('/data/singux-mcp-state-repair-20261010')
    backup = root / 'excel-16.before.json'
    assert not backup.exists(), 'Preserve original configuration'
    schema = sql("SELECT TABLE_SCHEMA FROM information_schema.tables WHERE TABLE_NAME='mcp_config'").strip()
    assert schema.replace('_', '').isalnum()
    table = schema + '.mcp_config'
    raw = sql('SELECT config FROM ' + table + " WHERE id=16 AND deploy_status='DeployFailed'").strip()
    assert raw
    cfg = json.loads(raw)
    server_cfg = json.loads(cfg['serverConfig'])
    servers = server_cfg['mcpServers']
    assert len(servers) == 1
    server = next(iter(servers.values()))
    assert server['command'] == 'npx'
    assert '@negokaz/excel-mcp-server' in server['args'] and '@mcp_hub_org/cli@latest' in server['args']
    assert not server.get('env'), 'Review unexpected Excel environment before changing launcher'
    fixed = copy.deepcopy(cfg)
    server['args'] = ['-y', '@negokaz/excel-mcp-server@0.12.0']
    fixed['serverConfig'] = json.dumps(server_cfg, ensure_ascii=False)
    payload = json.dumps({'mcpId': 'singux-excel-repair-16', 'mcpType': 'OneShot', 'mcpJsonConfig': fixed['serverConfig']})
    ready = False
    for attempt in range(24):
        p = subprocess.run(['docker', 'exec', '-i', 'singux-backend-1', 'curl', '-fsS', '--max-time', '15',
            '-H', 'Content-Type: application/json', '--data-binary', '@-',
            'http://mcp-proxy:8080/mcp/sse/check_status'], input=payload, text=True, capture_output=True)
        assert p.returncode == 0, 'Excel proxy startup check rejected'
        result = json.loads(p.stdout).get('data') or {}
        if result.get('status') == 'Ready':
            ready = True
            break
        assert result.get('status') != 'Error', 'Direct Excel package handshake failed; configuration unchanged'
        time.sleep(5)
    assert ready, 'Direct Excel startup timed out; configuration unchanged'
    js = """import {Client} from '/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import {SSEClientTransport} from '/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/sdk/dist/esm/client/sse.js';
const c=new Client({name:'excel-repair-check',version:'1'});
try { await c.connect(new SSEClientTransport(new URL('http://127.0.0.1:8080/mcp/sse/proxy/singux-excel-repair-16/sse')));
const tools=await c.listTools();if(!tools.tools.length)throw Error('No Excel tools');console.log(tools.tools.length);
} finally {await c.close();}
"""
    p = subprocess.run(['docker', 'exec', '-i', 'singux-mcp-proxy-1', 'node', '--input-type=module'],
                       input=js, capture_output=True, text=True, timeout=45)
    assert p.returncode == 0 and p.stdout.strip().isdigit(), 'Excel tool discovery failed; configuration unchanged'
    backup.write_text(raw)
    encode = lambda s: "CONVERT(UNHEX('" + s.encode().hex() + "') USING utf8mb4)"
    new = json.dumps(fixed, ensure_ascii=False)
    changed = sql('UPDATE ' + table + ' SET config=' + encode(new)
        + " WHERE id=16 AND deploy_status='DeployFailed' AND CAST(config AS CHAR)="
        + 'CAST(CAST(' + encode(raw) + ' AS JSON) AS CHAR); SELECT ROW_COUNT();').strip()
    assert changed == '1', 'Configuration changed concurrently; review retained backup'
    record = {'status': 'EXCEL_DIRECT_LAUNCHER_FIXED', 'id': 16, 'package': '@negokaz/excel-mcp-server@0.12.0',
              'handshakePassed': True, 'tools': int(p.stdout.strip()),
              'databaseStatus': 'DeployFailed', 'ownerRedeployRequired': True,
              'fileToolsExecuted': False, 'otherServicesChanged': False}
    (root / 'excel-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
