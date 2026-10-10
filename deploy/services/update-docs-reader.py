"""Update only bundled documentation, preserving business JS and backend containers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    assert p.returncode == 0, 'Documentation update command failed: ' + ' '.join(args[:3])
    return p.stdout


def main():
    os.umask(0o077)
    sha = json.load(sys.stdin)['sha256']
    root = Path('/data/singux-docs-reader-20261010-r2')
    release = root / 'release'
    assert not release.exists(), 'Preserve existing release'
    archive = root / 'reader.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == sha
    current = 'singux/frontend:1.1.10-20261010-docs-singletenant-r1'
    tag = 'singux/frontend:1.1.10-20261010-docs-singletenant-r2'
    front = json.loads(run(['docker', 'inspect', 'singux-frontend-1']))[0]
    assert front['Config']['Image'] == current
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id']
    labels = front['Config']['Labels']
    assert labels['com.docker.compose.project'] == 'singux'
    files = labels['com.docker.compose.project.config_files'].split(',')
    path = Path(files[-1])
    allowed = {Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64/compose.filing.json'),
               Path('/data/singux-migration-20261009/compose.app.test.json')}
    assert path in allowed and all(Path(f).is_file() for f in files)
    original = path.read_text()
    config = json.loads(original)
    assert config['services']['frontend']['image'] == current
    release.mkdir(mode=0o700)
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            dest = (release / item.name).resolve()
            assert dest.is_relative_to((release / 'docs').resolve())
            assert item.isfile() or item.isdir()
            if item.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(item) as inp, dest.open('xb') as out:
                    shutil.copyfileobj(inp, out)
    assert (release / 'docs/reader.js').is_file()
    (release / 'compose.before.json').write_text(original)
    (release / 'Dockerfile').write_text('FROM ' + current + '\nCOPY docs/ /usr/share/nginx/html/docs/\n'
                                      'RUN chmod -R a+rX /usr/share/nginx/html/docs\n')
    run(['docker', 'build', '-t', tag, str(release)])
    cmd = ['docker', 'compose', '-p', 'singux', '--project-directory', labels['com.docker.compose.project.working_dir']]
    envfile = labels.get('com.docker.compose.project.environment_file')
    if envfile:
        assert Path(envfile).is_file()
        cmd += ['--env-file', envfile]
    for f in files:
        cmd += ['-f', f]
    try:
        config['services']['frontend']['image'] = tag
        path.write_text(json.dumps(config, indent=2))
        run(cmd + ['config', '--quiet'])
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-t'])
        with urllib.request.urlopen('http://127.0.0.1:8080/docs/reader.js?v=2', timeout=30) as r:
            assert r.read() == (release / 'docs/reader.js').read_bytes()
        assert json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]['Id'] == backend
    except BaseException:
        path.write_text(original)
        run(cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'frontend'])
        raise
    result = {'status': 'DOCS_READER_UPDATED', 'image': tag, 'backendUnchanged': True, 'sha256': sha}
    (root / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
