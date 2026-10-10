import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('infra', Path(__file__).resolve().parents[1] / 'deploy/services/prepare-migration-infra.py')
infra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(infra)


class InfraConfigTests(unittest.TestCase):
    def source(self):
        return {'services': {name: {'image': 'sha256:test', 'ports': [{'published': '9999'}],
                    'volumes': [{'type': 'volume', 'source': name + '-data', 'target': '/data'}]}
                    for name in infra.SERVICES},
                'volumes': {name + '-data': {'name': 'singux_' + name + '-data'} for name in infra.SERVICES}}

    def test_only_expected_services_and_no_public_ports(self):
        original = self.source()
        unchanged = copy.deepcopy(original)
        result = infra.build(original)
        self.assertNotIn('mysql', result['services'])
        self.assertNotIn('backend', result['services'])
        self.assertTrue(all(not service['ports'] for service in result['services'].values()))
        self.assertTrue(result['networks']['default']['external'])
        self.assertEqual(original, unchanged)

    def test_refuse_host_bind(self):
        original = self.source()
        original['services']['redis']['volumes'][0]['type'] = 'bind'
        with self.assertRaises(AssertionError):
            infra.build(original)

    def test_refuse_dependency_that_would_start_business(self):
        original = self.source()
        original['services']['redis']['depends_on'] = {'backend': {}}
        with self.assertRaises(AssertionError):
            infra.build(original)


if __name__ == '__main__':
    unittest.main()
