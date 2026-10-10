"""Archive an exact log prefix off the full data disk, then deallocate only that prefix."""
import gzip
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remaining', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert subprocess.check_output(['hostname'], text=True).strip() == 'VM-0-15-opencloudos'
    container = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
    assert container['Config']['Labels']['com.docker.compose.project'] == 'singux'
    assert container['Config']['Labels']['com.docker.compose.project.working_dir'] == '/home/singu-x-1.1.10-20260924-r1-linux-amd64'
    destination = Path('/root/singux-log-recovery-20261011')
    destination.mkdir(mode=0o700, exist_ok=True)
    if args.remaining:
        assert json.loads((destination / 'result.json').read_text())['status'] == 'LOG_PREFIX_ARCHIVED_AND_DEALLOCATED'
    report = destination / ('remaining-result.json' if args.remaining else 'result.json')
    if report.exists():
        previous = json.loads(report.read_text())
        assert previous['status'] == 'LOG_PREFIX_ARCHIVED_AND_DEALLOCATED'
        print(json.dumps(previous)); return
    pid = container['State']['Pid']
    path = Path('/proc') / str(pid) / 'root/app/logs/app.log'
    before = path.stat()
    offset = 2 * 1024**3 if args.remaining else 0
    length = ((before.st_size - offset - 4 * 1024**2) // 4096 * 4096) if args.remaining else 2 * 1024**3
    assert length > 0 and before.st_size >= offset + length
    assert shutil.disk_usage(destination).free > length + 512 * 1024**2
    archive = destination / ('app.log.after-2GiB.gz' if args.remaining else 'app.log.first-2GiB.gz')
    digest = hashlib.sha256()
    with path.open('rb') as source, archive.open('xb') as output:
        source.seek(offset)
        with gzip.GzipFile(fileobj=output, mode='wb', compresslevel=1) as compressed:
            remaining = length
            while remaining:
                chunk = source.read(min(1024**2, remaining))
                assert chunk, 'Log became shorter; do not deallocate'
                digest.update(chunk)
                compressed.write(chunk)
                remaining -= len(chunk)
        output.flush()
        os.fsync(output.fileno())
    verified = hashlib.sha256()
    count = 0
    with gzip.open(archive, 'rb') as source:
        while chunk := source.read(1024**2):
            verified.update(chunk)
            count += len(chunk)
    assert count == length and verified.digest() == digest.digest()
    after = path.stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert after.st_size >= before.st_size
    # Hole punching keeps the inode, file length and all concurrent append writes.
    subprocess.run(['fallocate', '--punch-hole', '--keep-size', '--offset', str(offset),
                    '--length', str(length), str(path)], check=True)
    result = {'status': 'LOG_PREFIX_ARCHIVED_AND_DEALLOCATED', 'archivedBytes': length,
              'offset': offset,
              'sha256': digest.hexdigest(), 'archive': str(archive),
              'fileLengthPreserved': path.stat().st_size >= before.st_size,
              'databaseChanged': False, 'servicesStopped': False,
              'dataFreeBytes': shutil.disk_usage('/data').free}
    report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
