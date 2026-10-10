import hashlib
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'singux-knowledge-singletenant-20261007'
source = ROOT / 'outputs/knowledge-hotfix-20261007'
release = ROOT / 'outputs' / NAME
release.mkdir(exist_ok=True)
(release / 'runtime').mkdir(exist_ok=True)
for name in ('Dockerfile', 'app.jar'):
    shutil.copyfile(source / 'runtime' / name, release / 'runtime' / name)
shutil.copyfile(source / 'release.json', release / 'release.json')
shutil.copyfile(ROOT / 'deploy/update-knowledge.py', release / 'update-knowledge.py')
shutil.copyfile(ROOT / 'deploy/KNOWLEDGE_HOTFIX.md', release / 'README.md')
files = [release / p for p in ('runtime/Dockerfile', 'runtime/app.jar', 'release.json', 'update-knowledge.py', 'README.md')]
def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()
(release / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + p.relative_to(release).as_posix() + '\n' for p in files), encoding='ascii')
archive = ROOT / 'outputs' / (NAME + '.tar.gz')
with tarfile.open(archive, 'w:gz') as target:
    for path in files + [release / 'SHA256SUMS']:
        target.add(path, arcname=NAME + '/' + path.relative_to(release).as_posix(), recursive=False)
checksum = sha(archive)
Path(str(archive) + '.sha256').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
print('Package: ' + str(archive))
print('Bytes: ' + str(archive.stat().st_size))
print('SHA256: ' + checksum)
