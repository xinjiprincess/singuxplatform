"""Verify exported Docker tags and image config digests against package metadata."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

folder = Path(sys.argv[1])
expected = json.loads((folder / 'images.json').read_text(encoding='utf-8'))['images']
with tarfile.open(folder / 'images.tar', 'r:') as archive:
    manifest = json.load(archive.extractfile('manifest.json'))
    assert len(manifest) == len(expected), 'Unexpected number of exported images'
    for image in expected:
        matched = [item for item in manifest if image['tag'] in (item.get('RepoTags') or [])]
        assert len(matched) == 1, 'Missing or duplicate image tag: ' + image['tag']
        config = archive.extractfile(matched[0]['Config']).read()
        assert 'sha256:' + hashlib.sha256(config).hexdigest() == image['id'], 'Image config checksum mismatch'
        parsed = json.loads(config)
        assert parsed['architecture'] == image['architecture'] == 'amd64'
        assert parsed['os'] == image['os'] == 'linux'
        print('PASS: exported Linux amd64 image ' + image['tag'])
