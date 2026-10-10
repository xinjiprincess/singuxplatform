"""Exercise a private MCP fixture and public login/config routes without user data."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request

backend = 'singux-backend-1'
proxy = 'singux-mcp-proxy-1'
config = {'mcpServers': {'filesystem': {'command': 'node', 'args': [
    '/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js', '/tmp']}}}
payload = json.dumps({'mcpId': 'singux-local-smoke', 'mcpType': 'OneShot', 'mcpJsonConfig': json.dumps(config)})
ready = False
for attempt in range(30):
    raw = subprocess.check_output(['docker', 'exec', '-i', backend, 'curl', '-fsS', '--max-time', '15',
        '-H', 'Content-Type: application/json', '--data-binary', '@-', 'http://mcp-proxy:8080/mcp/sse/check_status'], input=payload.encode())
    response = json.loads(raw)
    state = response.get('data', {}).get('status')
    if state == 'Error': raise RuntimeError('MCP fixture deployment returned Error')
    if state == 'Ready': ready = True; break
    time.sleep(2)
if not ready: raise RuntimeError('MCP fixture deployment timed out')
source = Path(__file__).with_name('smoke-call.mjs').read_bytes()
subprocess.run(['docker', 'exec', '-i', '-e',
    'MCP_SDK_CLIENT=/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/sdk/dist/esm/client/',
    proxy, 'node', '--input-type=module'], input=source, check=True)
print('MCP_PRODUCTION_TOOL_CALL_OK', flush=True)
if '--public' in __import__('sys').argv:
    for path in ('/login', '/api/tenant/config'):
        request = urllib.request.Request('http://127.0.0.1:8080' + path, headers={'Host': 'www.ciyuancenter.cc'})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            if response.status != 200 or not body: raise RuntimeError('Public route did not return content')
            if path.endswith('/config'):
                result = json.loads(body)
                if result.get('code') != '0000': raise RuntimeError('Public tenant configuration failed')
        print('PUBLIC_ROUTE_OK ' + path, flush=True)
