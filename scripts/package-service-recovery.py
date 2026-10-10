"""Export tested images; do not copy databases, environment files or SSH credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--computer', action='store_true')
    parser.add_argument('--mcp', action='store_true')
    args = parser.parse_args()
    if args.computer and args.mcp:
        parser.error('--computer and --mcp are separate packages')
    name = ('singux-service-recovery-mcp-singletenant-20261009' if args.mcp else
            'singux-' + ('computer-local' if args.computer else 'service-recovery-singletenant') + '-20261008')
    folder = ROOT / 'outputs' / name
    folder.mkdir(parents=True, exist_ok=True)
    images = (['singux/rcoder:20260929-local', 'singux/computer-runner:20261008-local'] if args.computer
              else ['singux/backend:1.1.10-20261008-service-recovery-r1'])
    if args.mcp:
        images = ['singux/backend:1.1.10-20261009-service-recovery-mcp-r1',
                  'singux/mcp-proxy:0.2.8-20261009-recovery-r1']
    info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', *images]))
    report = {'images': [{'tag': tag, 'id': item['Id'], 'architecture': item['Architecture'], 'os': item['Os']} for tag, item in zip(images, info)],
              'productionApproved': False, 'containsDatabase': False, 'containsCredentials': False}
    (folder / 'images.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / ('deploy/mcp/RECOVERY.md' if args.mcp else 'deploy/SERVICE_RECOVERY.md'), folder / 'README.md')
    if not args.computer:
        source = 'outputs/service-recovery-mcp-20261009' if args.mcp else 'outputs/service-recovery-20261008'
        shutil.copyfile(ROOT / source / 'release.json', folder / 'release.json')
    if args.mcp:
        shutil.copyfile(ROOT / 'deploy/mcp/compose.recovery.json', folder / 'compose.mcp.json')
        shutil.copyfile(ROOT / 'deploy/mcp/sources.json', folder / 'mcp-sources.json')
    subprocess.run(['docker', 'save', '-o', str(folder / 'images.tar'), *images], check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/verify-service-images.py'), str(folder)], check=True)
    paths = sorted(p for p in folder.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (folder / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + p.name + '\n' for p in paths), encoding='ascii')
    archive = folder.with_suffix('.tar.gz')
    with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
        for path in paths + [folder / 'SHA256SUMS']:
            tar.add(path, arcname=name + '/' + path.name, recursive=False)
    checksum = sha(archive)
    Path(str(archive) + '.sha256').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': checksum}, indent=2), flush=True)

if __name__ == '__main__':
    main()
