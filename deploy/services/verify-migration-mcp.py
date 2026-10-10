"""Exercise the isolated MCP fixture on the target, without editing user services."""
import json
from pathlib import Path
import subprocess

ROOT = Path('/data/singux-migration-20261009')


def main():
    result = subprocess.run(['python3', str(ROOT / 'mcp-check/verify-production.py')],
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, 'MCP fixture failed: ' + result.stderr[-800:]
    assert 'MCP_PRODUCTION_TOOL_CALL_OK' in result.stdout
    record = {'status': 'MCP_PRIVATE_TOOL_CALL_VERIFIED', 'passed': True,
              'backendToProxy': True, 'sseHandshake': True, 'toolList': True,
              'readOnlyToolCall': True, 'fixture': 'isolated filesystem /tmp',
              'userServiceConfigurationsChanged': False, 'sourceChanged': False,
              'allUserServicesVerified': False}
    (ROOT / 'mcp-verification.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
