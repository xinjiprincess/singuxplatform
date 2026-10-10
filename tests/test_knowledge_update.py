import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/update-knowledge.py'
spec = importlib.util.spec_from_file_location('knowledge_update', SCRIPT)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)

class UpdateTests(unittest.TestCase):
    def exercise(self, apply=False, failure=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deployment = root / 'deployment'
            release = root / 'release'
            backups = root / 'backups'
            deployment.mkdir()
            (release / 'runtime').mkdir(parents=True)
            (release / 'runtime/app.jar').write_bytes(b'patched jar')
            manifest = {'image': update.IMAGE, 'schemaUnchanged': True, 'dataBackwardCompatible': True,
                        'baselineJarSha256': update.BASE_JAR,
                        'patchedJarSha256': update.sha(release / 'runtime/app.jar')}
            if failure == 'checksum':
                manifest['patchedJarSha256'] = '0' * 64
            (release / 'release.json').write_text(json.dumps(manifest))
            (deployment / '.env').write_text('NO_REAL_CREDENTIALS=true\n')
            services = ['frontend', 'backend', 'mysql', 'elasticsearch', 'milvus', 'etcd', 'minio', 'redis']
            original = {'name': 'singux', 'services': {s: {'image': 'old-' + s} for s in services}}
            (deployment / 'compose.json').write_text(json.dumps(original))
            containers = []
            for service in services:
                mounts = [{'Type': 'volume', 'Name': 'singux_' + service + '-data', 'Destination': '/data', 'RW': True}]
                if service == 'backend':
                    mounts = [{'Type': 'volume', 'Name': 'singux_backend-uploads', 'Destination': '/data/uploads', 'RW': True}]
                    if failure == 'bind':
                        mounts.append({'Type': 'bind', 'Source': '/wrong.jar', 'Destination': '/app/app.jar', 'RW': False})
                containers.append({'Id': service, 'Image': update.BASE_MANIFEST if service == 'backend' else 'old-' + service,
                                   'State': {'Status': 'running', 'Health': {'Status': 'healthy'}}, 'Mounts': mounts,
                                   'Config': {'Labels': {'com.docker.compose.project': 'singux', 'com.docker.compose.service': service,
                                                        'com.docker.compose.project.working_dir': str(deployment)}}})
            commands = []
            failed_once = False
            def fake_run(args, stdout=None):
                nonlocal failed_once
                commands.append(args)
                if args[:2] == ['docker', 'inspect']:
                    return json.dumps(containers)
                if args[:3] == ['docker', 'image', 'inspect']:
                    return json.dumps([{'Id': 'sha256:new-patch'}])
                if 'compose' in args:
                    if 'ps' in args:
                        return 'new-backend' if args[-1] == 'backend' else ' '.join(services)
                    if 'up' in args and failure == 'health' and not failed_once:
                        failed_once = True
                        raise RuntimeError('simulated health failure')
                    return ''
                if args[:2] == ['docker', 'exec'] and 'sha256sum' in args:
                    value = manifest['patchedJarSha256'] if args[2] == 'new-backend' else update.BASE_JAR
                    return value + ' /app/app.jar'
                if 'du -sk /source' in args:
                    return '64 /source'
                if stdout is not None and hasattr(stdout, 'write'):
                    if failure == 'backup':
                        raise RuntimeError('simulated backup failure')
                    stdout.write(b'isolated mock backup, not actual data')
                return ''
            class Space:
                free = 100 * 1024 ** 3
            def routed_path(value):
                return backups if str(value) == '/data/singux-backups' else Path(value)
            argv = ['update', str(deployment), str(release)] + (['--apply'] if apply else [])
            with patch.object(sys, 'argv', argv), patch.object(update, 'run', side_effect=fake_run), \
                 patch.object(update, 'Path', side_effect=routed_path), patch.object(update.os.path, 'ismount', return_value=True), \
                 patch.object(update.shutil, 'disk_usage', return_value=Space()):
                if failure:
                    with self.assertRaises(RuntimeError):
                        update.main()
                else:
                    update.main()
            current = json.loads((deployment / 'compose.json').read_text())
            if failure in ('checksum', 'bind') or not apply:
                self.assertFalse(any('stop' in c or 'build' in c for c in commands))
                self.assertEqual(current, original)
            elif failure:
                self.assertEqual(current['services']['backend']['image'], update.BASE_MANIFEST)
                self.assertTrue(any('up' in c for c in commands))
            else:
                self.assertEqual(current['services']['backend']['image'], 'sha256:new-patch')
                self.assertEqual(current['services']['frontend']['image'], 'old-frontend')
                self.assertEqual(len(list(backups.glob('*/BACKUP_COMPLETE'))), 1)
                self.assertEqual(len(list(backups.glob('*/*.tar.gz'))), 8)
            self.assertFalse((deployment / '.knowledge-update-lock').exists())
            self.assertFalse(any('down' in c or 'prune' in c for c in commands))

    def test_read_only(self): self.exercise()
    def test_checksum_rejected_before_stop(self): self.exercise(apply=True, failure='checksum')
    def test_executable_bind_rejected(self): self.exercise(apply=True, failure='bind')
    def test_success_backs_up_all_stores(self): self.exercise(apply=True)
    def test_backup_failure_restores_old_services(self): self.exercise(apply=True, failure='backup')
    def test_health_failure_restores_images_not_data(self): self.exercise(apply=True, failure='health')

if __name__ == '__main__':
    unittest.main()
