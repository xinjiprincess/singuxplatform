"""Exclude verified old Chromium runtime sockets/locks in target staging only."""
import json
import os
from pathlib import Path, PurePosixPath
import re

ROOT = Path('/data/singux-migration-20261009')


def main():
    os.umask(0o077)
    result_path = ROOT / 'workspace-staging-result.json'
    result = json.loads(result_path.read_text())
    assert result['status'] == 'WORKSPACE_LINK_REVIEW'
    links = json.loads((ROOT / 'workspace-quarantined-links.json').read_text())
    assert len(links) == result['quarantinedLinkCount']
    for link in links:
        assert PurePosixPath(link['path']).name == 'SingletonSocket'
        assert re.fullmatch(r'/tmp/org\.chromium\.Chromium\.[A-Za-z0-9]+/SingletonSocket', link['target'])
        assert link['reason'] == 'AbsoluteLinkError'
    base = ROOT / 'workspace-staged'
    removed = 0
    for link in links:
        parent = (base / link['path']).parent
        assert parent.resolve().is_relative_to(base.resolve())
        for name in ['SingletonLock', 'SingletonCookie']:
            path = parent / name
            if path.is_symlink():
                path.unlink()
                removed += 1
            else:
                assert not path.exists(), 'Unexpected regular browser lock; preserve and review'
    result.update(status='WORKSPACE_SAFE_STAGED',
                  excludedOldBrowserSockets=len(links), removedOldBrowserLockLinks=removed,
                  originalArchivePreserved=True, restoredToLiveServices=False)
    result_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
