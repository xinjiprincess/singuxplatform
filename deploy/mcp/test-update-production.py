"""Exercise backup, gate and rollback behavior without connecting to production."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import tarfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('update', Path(__file__).with_name('update-production.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class UpdateTest(unittest.TestCase):
    def exercise(self, fail=None, apply=True, bad_checksum=False):
        with tempfile.TemporaryDirectory(prefix='singux-mcp-update-test-') as tmp:
            root = Path(tmp); deployment = root / 'deployment'; deployment.mkdir()
            (deployment / 'compose.json').write_text(json.dumps({'services': {n: {'image': 'old'} for n in
                ('backend', 'frontend', 'mysql', 'redis', 'elasticsearch', 'minio', 'milvus', 'etcd')}}))
            (deployment / '.env').write_text('TEST_ONLY=1\n')
            services = {n: {'Id': n + '-id', 'Image': 'old-' + n, 'Mounts': []} for n in
                ('backend', 'frontend', 'mysql', 'redis', 'elasticsearch', 'minio', 'milvus', 'etcd')}
            context = {'DEPLOY': deployment, 'services': services, 'volumes': {'test-volume'},
                       'backend': services['backend'], 'compose': ['docker', 'compose'], 'BASE_JAR': 'baseline'}
            release = root / 'singux-service-recovery-mcp-singletenant-20261009'; release.mkdir()
            (release / 'release.json').write_text(json.dumps({'baselineJarSha256': 'baseline', 'patchedJarSha256': module.JAR_SHA, 'schemaUnchanged': True}))
            (release / 'images.json').write_text(json.dumps({'images': [{'tag': tag, 'id': tag + '-id'} for tag in (module.BACKEND_TAG, module.MCP_TAG)]}))
            (release / 'compose.mcp.json').write_text(json.dumps({'services': {'backend': {}, 'mcp-proxy': {}}}))
            checksum = hashlib.sha256((release / 'release.json').read_bytes()).hexdigest()
            (release / 'SHA256SUMS').write_text(('0' * 64 if bad_checksum else checksum) + '  release.json\n')
            calls = []; counts = {'user': 161}
            def fake_run(args, output=None, source=None):
                calls.append(args)
                if fail == 'backup' and 'mysqldump' in ' '.join(args): raise RuntimeError('Simulated backup failure')
                if fail == 'health' and 'up' in args and args[-1] == 'backend' and args[0] == 'docker':
                    raise RuntimeError('Simulated new backend health failure')
                if output is not None:
                    if hasattr(output, 'write'): output.write(b'test archive')
                    return ''
                if args[:3] == ['docker', 'image', 'inspect']:
                    return json.dumps([{'Id': args[3] + '-id', 'Os': 'linux', 'Architecture': 'amd64'}])
                if args[:2] == ['docker', 'inspect']:
                    return json.dumps([{'Mounts': []}])
                if 'sha256sum' in args: return module.JAR_SHA + ' /app/app.jar'
                if args[-2:] == ['-q', 'backend']: return 'backend-id'
                if '-q' in args: return args[-1] + '-id'
                return ''
            original_path = Path
            def mapped_path(value):
                return root / 'backups' if value == '/data/singux-backups' else original_path(value)
            fake_signal = types.SimpleNamespace(SIGTERM=15, SIGINT=2, SIGHUP=1, signal=lambda n, h: None)
            with patch.object(module, '__file__', str(root / 'update-production.py')), patch.object(module, 'Path', mapped_path), \
                 patch.object(module.runpy, 'run_path', return_value=context), patch.object(module, 'run', side_effect=fake_run), \
                 patch.object(module, 'image_ids', side_effect=lambda release, expected: {expected['id']}), \
                 patch.object(module, 'counts', return_value=counts), patch.object(module, 'signal', fake_signal), \
                 patch.object(module.sys, 'argv', ['test'] + (['--apply'] if apply else [])):
                if fail or bad_checksum:
                    with self.assertRaises(RuntimeError): module.main()
                else: module.main()
            if not apply or bad_checksum:
                self.assertFalse(any('stop' in c for c in calls))
            elif fail:
                self.assertFalse((deployment / 'compose.mcp.json').exists())
                rollback = json.loads((deployment / 'compose.json').read_text())
                self.assertEqual(rollback['services']['backend']['image'], 'old-backend')
                self.assertFalse(any('mysql' in c and 'restore' in c for c in calls))
            else:
                self.assertTrue((root / 'deployment-result.json').exists())
                self.assertTrue((deployment / 'compose.mcp.json').exists())
                proxy = json.loads((deployment / 'compose.mcp.json').read_text())['services']['mcp-proxy']
                self.assertEqual(proxy['pids_limit'], 512)
                self.assertEqual(proxy['mem_limit'], '1536m')
                self.assertEqual(proxy['environment']['TOKIO_WORKER_THREADS'], '2')
            self.assertFalse((deployment / '.mcp-recovery-lock').exists())

    def test_check_only(self): self.exercise(apply=False)
    def test_checksum_refusal(self): self.exercise(bad_checksum=True)
    def test_success(self): self.exercise()
    def test_backup_failure_rollback(self): self.exercise(fail='backup')
    def test_health_failure_rollback(self): self.exercise(fail='health')

class ImageIdentityTest(unittest.TestCase):
    def exercise(self, corrupt_config=False, corrupt_manifest=False):
        config = b'{"architecture":"amd64","os":"linux"}'
        config_id = 'sha256:' + hashlib.sha256(config).hexdigest()
        blob = json.dumps({'config': {'digest': config_id}}).encode()
        manifest_id = 'sha256:' + hashlib.sha256(blob).hexdigest()
        files = {
            'manifest.json': json.dumps([{'RepoTags': ['test:1'], 'Config': 'config.json'}]).encode(),
            'config.json': b'corrupt' if corrupt_config else config,
            'index.json': json.dumps({'manifests': [{'digest': manifest_id}]}).encode(),
            'blobs/sha256/' + manifest_id[7:]: b'corrupt' if corrupt_manifest else blob,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with tarfile.open(root / 'images.tar', 'w') as archive:
                for name, data in files.items():
                    member = tarfile.TarInfo(name); member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            if corrupt_config or corrupt_manifest:
                with self.assertRaises(RuntimeError): module.image_ids(root, {'tag': 'test:1', 'id': config_id})
            else:
                self.assertEqual(module.image_ids(root, {'tag': 'test:1', 'id': config_id}), {config_id, manifest_id})

    def test_config_and_oci_ids(self): self.exercise()
    def test_corrupt_config_refused(self): self.exercise(corrupt_config=True)
    def test_corrupt_manifest_refused(self): self.exercise(corrupt_manifest=True)

if __name__ == '__main__': unittest.main()
