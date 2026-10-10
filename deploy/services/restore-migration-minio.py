"""Restore exported objects through MinIO API; credentials stay in process memory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import urllib.parse

ROOT = Path('/data/singux-migration-20261009')
EXPORT = ROOT / 'business-staged/business-export'
TMP = '/tmp/singux-migration-objects-20261009'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert json.loads((ROOT / 'business-staging-result.json').read_text())['status'] == 'BUSINESS_CORE_STAGED'
    assert 'singux-backend-1' not in subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True).splitlines()
    network = json.loads(subprocess.check_output(['docker', 'network', 'inspect', 'singux_default']))[0]
    assert network['Internal']
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-minio-1']))[0]
    assert container['State']['Running']
    env = dict(item.split('=', 1) for item in container['Config']['Env'])
    address = ('http://' + urllib.parse.quote(env['MINIO_ROOT_USER'], safe='') + ':'
               + urllib.parse.quote(env['MINIO_ROOT_PASSWORD'], safe='') + '@127.0.0.1:9000')

    def mc(arguments):
        # stdin avoids credentials in docker-exec arguments or an alias config file.
        command = 'export MC_HOST_migration=' + shlex.quote(address) + '\nexec ' + shlex.join(
                    ['mc', '--config-dir', TMP + '/config', *arguments]) + '\n'
        process = subprocess.run(['docker', 'exec', '-i', 'singux-minio-1', 'sh', '-s'],
                                 input=command.encode(), capture_output=True, timeout=180)
        assert process.returncode == 0, 'MinIO migration command failed; credential-bearing output suppressed'
        return process.stdout

    buckets = json.loads((EXPORT / 'minio-buckets.json').read_text())
    assert all(name and '/' not in name and name not in {'.', '..'} for name in buckets)
    result_path = ROOT / 'minio-restore-result.json'
    if args.resume:
        result = json.loads(result_path.read_text())
        assert result['status'] == 'MINIO_RESTORING'
    else:
        assert not result_path.exists()
        result = {'status': 'MINIO_RESTORING', 'ownedBuckets': [], 'verifiedBuckets': [],
                  'objects': 0, 'bytes': 0, 'sourceChanged': False}
        subprocess.run(['docker', 'exec', 'singux-minio-1', 'sh', '-c',
                        'test ! -e ' + TMP + ' && mkdir -m 700 ' + TMP], check=True)
        subprocess.run(['docker', 'cp', str(EXPORT / 'minio-objects') + '/.',
                        'singux-minio-1:' + TMP + '/objects'], check=True, stdout=subprocess.DEVNULL)

    def checkpoint():
        temporary = result_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2))
        temporary.replace(result_path)

    checkpoint()
    for bucket in buckets:
        if bucket in result['verifiedBuckets']:
            continue
        files = {}
        directory = EXPORT / 'minio-objects' / bucket
        for path in directory.rglob('*'):
            assert not path.is_symlink() and (path.is_dir() or path.is_file())
            if path.is_file():
                files[path.relative_to(directory).as_posix()] = path
        mc(['mb', '--ignore-existing', 'migration/' + bucket])
        listing = mc(['ls', '--recursive', '--json', 'migration/' + bucket]).decode()
        existing = set()
        for line in listing.splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            assert entry.get('status') == 'success'
            if entry.get('type') == 'file':
                existing.add(entry['key'])
        if bucket not in result['ownedBuckets']:
            assert not existing.intersection(files), 'Refuse overwriting pre-existing exported object keys'
            result['ownedBuckets'].append(bucket)
            checkpoint()
        mc(['mirror', '--overwrite', '--json', TMP + '/objects/' + bucket, 'migration/' + bucket])
        total = 0
        for key, path in files.items():
            data = mc(['cat', 'migration/' + bucket + '/' + key])
            assert len(data) == path.stat().st_size
            with path.open('rb') as source:
                expected = hashlib.file_digest(source, 'sha256').hexdigest()
            assert hashlib.sha256(data).hexdigest() == expected, 'MinIO object readback hash mismatch'
            total += len(data)
        result['objects'] += len(files)
        result['bytes'] += total
        result['verifiedBuckets'].append(bucket)
        checkpoint()
    result.update(status='MINIO_EXPORTED_OBJECTS_RESTORED', allObjectHashesMatched=True,
                  notLatestSourceSnapshot=True, legacyVectorObjectsNotProofOfIndexRestore=True)
    checkpoint()
    print(json.dumps({key: result[key] for key in ['status', 'objects', 'bytes', 'allObjectHashesMatched']}), flush=True)


if __name__ == '__main__':
    main()
