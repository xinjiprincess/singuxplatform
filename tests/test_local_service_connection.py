import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('local_connection', Path(__file__).resolve().parents[1] / 'deploy/services/connect-local-backend.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConnectionTests(unittest.TestCase):
    def backend(self):
        return {'HostConfig': {'PortBindings': {}, 'Privileged': False},
                'NetworkSettings': {'Networks': {'singux-local_default': {}}},
                'Config': {'Env': [
                    'BUILD_SERVER_URL=http://singux-file-service:60000/api',
                    'AI_AGENT_URL=http://singux-rcoder:8090',
                    'DOCKER_PROXY_URL=http://singux-rcoder:8088',
                    'MCP_PROXY_URL=http://singux-mcp:8080',
                    'CODE_EXECUTE_URL=http://singux-mcp:8080/api/run_code_with_log']},
                'State': {'Health': {'Status': 'healthy'}}}

    def test_idempotent_does_not_replace(self):
        backend = self.backend()
        mcp = {'NetworkSettings': {'Networks': {'singux-local_default': {}}}}
        with patch.object(module, 'docker', side_effect=[json.dumps([backend]), json.dumps([mcp])]) as run:
            module.main()
            self.assertEqual(run.call_count, 2)

    def test_unexpected_network_rejected_before_change(self):
        backend = self.backend()
        backend['NetworkSettings']['Networks']['production'] = {}
        with patch.object(module, 'docker', return_value=json.dumps([backend])) as run:
            with self.assertRaises(RuntimeError):
                module.main()
            self.assertEqual(run.call_count, 1)

    def test_privileged_backend_rejected(self):
        backend = self.backend()
        backend['HostConfig']['Privileged'] = True
        with patch.object(module, 'docker', return_value=json.dumps([backend])) as run:
            with self.assertRaises(RuntimeError):
                module.main()
            self.assertEqual(run.call_count, 1)

    def test_unhealthy_idempotent_backend_rejected(self):
        backend = self.backend()
        backend['State']['Health']['Status'] = 'unhealthy'
        mcp = {'NetworkSettings': {'Networks': {'singux-local_default': {}}}}
        with patch.object(module, 'docker', side_effect=[json.dumps([backend]), json.dumps([mcp])]):
            with self.assertRaises(RuntimeError):
                module.main()


if __name__ == '__main__':
    unittest.main()
