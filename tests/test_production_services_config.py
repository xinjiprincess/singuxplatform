import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare', ROOT / 'deploy/services/prepare-production.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
verify_spec = importlib.util.spec_from_file_location('verify', ROOT / 'deploy/services/verify-production-runtime.py')
verify = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(verify)


class ProductionConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.here = Path(self.temp.name)
        for name in ['rcoder.yml', 'gateway.conf']:
            (self.here / name).write_bytes((ROOT / 'deploy/services' / name).read_bytes())
        with patch.object(prepare, 'HERE', self.here):
            prepare.main()
        self.config = json.loads((self.here / 'rcoder.production.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def test_separate_execution_network(self):
        self.assertEqual(self.config['docker_config']['network_mode'], 'singux-execution')
        for service in self.config['docker_config']['multi_image_config']['services'].values():
            self.assertEqual(service['network_mode'], 'singux-execution')

    def test_bounded_resources_and_security(self):
        for service in self.config['docker_config']['multi_image_config']['services'].values():
            self.assertFalse(service['security']['privileged'])
            self.assertEqual(service['security']['pids_limit'], 256)
            limits = service['resource_limits']
            self.assertLessEqual(limits['memory_limit'], 1610612736)
            self.assertEqual(limits['swap_limit'], limits['memory_limit'] * 2)

    def test_no_direct_fixture_listener(self):
        gateway = (self.here / 'gateway.production.conf').read_text()
        self.assertNotIn('listen 4000;', gateway)
        self.assertIn('listen 8088;', gateway)
        self.assertIn('listen 60000;', gateway)

    def test_local_files_preserved(self):
        self.assertEqual((self.here / 'rcoder.yml').read_bytes(), (ROOT / 'deploy/services/rcoder.yml').read_bytes())

    def test_fixture_already_removed(self):
        with patch.object(verify, 'docker', return_value='') as docker:
            verify.remove_fixture('fixture')
            docker.assert_called_once_with('ps', '-a', '--format', '{{.Names}}')

    def test_fixture_async_auto_removal(self):
        with patch.object(verify, 'docker', side_effect=['fixture', '', 'fixture', '']), \
             patch.object(verify.subprocess, 'run') as remove, patch.object(verify.time, 'sleep'):
            remove.return_value.returncode = 1
            verify.remove_fixture('fixture')
            remove.assert_called_once_with(['docker', 'rm', 'fixture'], capture_output=True)


if __name__ == '__main__':
    unittest.main()
