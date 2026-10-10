"""Target-only workspace extraction with escaping links quarantined, not followed."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile

ROOT = Path('/data/singux-migration-20261009')


def main():
    os.umask(0o077)
    expected = json.loads((ROOT / 'business-staging-result.json').read_text())
    assert expected['status'] == 'BUSINESS_CORE_STAGED'
    with (ROOT / 'business.tar.gz').open('rb') as file:
        assert hashlib.file_digest(file, 'sha256').hexdigest() == expected['sha256']
    temporary = ROOT / 'workspace-staged.partial'
    destination = ROOT / 'workspace-staged'
    assert not temporary.exists() and not destination.exists(), 'Refuse overwrite'
    assert shutil.disk_usage(ROOT).free > 6 * 1024**3
    temporary.mkdir(mode=0o700)
    count = 0
    quarantined = []
    with tarfile.open(ROOT / 'business.tar.gz', 'r|gz') as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert path.parts and not path.is_absolute() and '..' not in path.parts
            if path.parts[0] != 'workspace':
                continue
            assert not member.isdev() and not member.isfifo(), 'Special file refused'
            try:
                tar.extract(member, temporary, filter='data')
            except (tarfile.AbsoluteLinkError, tarfile.LinkOutsideDestinationError) as error:
                # Preserve original archive and a private inventory for explicit review.
                assert member.issym() or member.islnk()
                quarantined.append({'path': member.name, 'target': member.linkname,
                                    'reason': type(error).__name__})
                continue
            count += 1
    assert (temporary / 'workspace').is_dir()
    temporary.rename(destination)
    (ROOT / 'workspace-quarantined-links.json').write_text(json.dumps(quarantined, indent=2))
    record = {'status': 'WORKSPACE_STAGED' if not quarantined else 'WORKSPACE_LINK_REVIEW',
              'extractedEntries': count, 'quarantinedLinkCount': len(quarantined),
              'originalArchivePreserved': True, 'restoredToLiveServices': False}
    (ROOT / 'workspace-staging-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
