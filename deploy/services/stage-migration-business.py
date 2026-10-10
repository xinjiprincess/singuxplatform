"""Target-only safe staging; never writes to a live volume or starts a service."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile

ROOT = Path('/data/singux-migration-20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    archive = ROOT / 'business.tar.gz'
    received = json.loads((ROOT / 'business-receive-result.json').read_text())
    assert received['status'] == 'BUSINESS_ARCHIVE_STAGED'
    assert args.sha256 == received['sha256']
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    assert digest == args.sha256, 'Archive SHA256 mismatch'
    destination = ROOT / 'business-staged'
    temporary = ROOT / 'business-staged.partial'
    assert not destination.exists() and not temporary.exists(), 'Preserve existing staging; inspect before retry'
    assert shutil.disk_usage(ROOT).free > 6 * 1024**3, 'Insufficient staging space'
    temporary.mkdir(mode=0o700)
    count = 0
    skipped_workspace = 0
    allowed = {'business-export', 'backend-uploads', 'singu-download-site'}
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts and path.parts
            if path.parts[0] == 'workspace':
                skipped_workspace += 1
                continue
            assert path.parts[0] in allowed, 'Unexpected archive prefix'
            assert not member.isdev() and not member.isfifo(), 'Special file refused'
            tar.extract(member, path=temporary, filter='data')
            count += 1
    assert (temporary / 'business-export/configs/platform-resolved.json').is_file()
    assert (temporary / 'business-export/search/result.json').is_file()
    assert (temporary / 'backend-uploads').is_dir()
    temporary.rename(destination)
    record = {'status': 'BUSINESS_CORE_STAGED', 'sha256': digest,
              'extractedEntries': count, 'workspaceDeferredEntries': skipped_workspace,
              'restoredToLiveServices': False, 'workspaceRestored': False,
              'targetPlatformStarted': False}
    (ROOT / 'business-staging-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
