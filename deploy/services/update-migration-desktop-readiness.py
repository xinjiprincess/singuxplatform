"""Patch only the target computer launcher and idle RCoder image selection."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

ROOT = Path('/data/singux-migration-20261009')
DEST = ROOT / 'desktop-readiness-20261010'
CONFIG = Path('/data/singux-update/services-runtime-20261009-r1/rcoder.private.json')
OLD = 'singux/computer-runner:20261008-local'
NEW = 'singux/computer-runner:20261010-readiness-r1'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    record = DEST / 'result.json'
    if record.exists():
        assert json.loads(record.read_text())['status'] == 'DESKTOP_READINESS_PATCHED'
        print(record.read_text()); return
    assert not (DEST / 'config.before.json').exists(), 'Incomplete patch requires review'
    running = docker('ps', '-a', '--format', '{{.Names}}').splitlines()
    assert not any(n.startswith(('computer-agent-runner-', 'web-agent-runner-')) for n in running)
    rcoder = json.loads(docker('inspect', 'singux-runtime-rcoder-1'))[0]
    assert rcoder['Config']['Labels']['com.docker.compose.project'] == 'singux-runtime'
    assert any(m['Source'] == str(CONFIG) for m in rcoder['Mounts'])
    before_ids = docker('ps', '-q', '--no-trunc').splitlines()
    before = CONFIG.read_bytes()
    config = json.loads(before)
    service = config['docker_config']['multi_image_config']['services']['computer-agent-runner']
    for field in ('image', 'default_image', 'amd64_image'):
        assert service[field] == OLD
        service[field] = NEW
    base = json.loads(docker('image', 'inspect', OLD))[0]['Id']
    launcher = DEST / 'start.sh'
    assert launcher.is_file()
    (DEST / 'Dockerfile').write_text('FROM ' + base + '\nCOPY start.sh /app/start-computer.sh\n'
                                    'RUN chmod 755 /app/start-computer.sh && bash -n /app/start-computer.sh\n')
    build = subprocess.run(['docker', 'build', '--network=none', '-t', NEW, str(DEST)],
                           capture_output=True, timeout=180)
    assert build.returncode == 0, 'Launcher image build failed; runtime unchanged'
    (DEST / 'config.before.json').write_bytes(before)
    destination = next(m['Destination'] for m in rcoder['Mounts'] if m['Source'] == str(CONFIG))
    updated = json.dumps(config, indent=2).encode()
    try:
        CONFIG.write_bytes(updated)
        docker('restart', 'singux-runtime-rcoder-1')
        for _ in range(60):
            current = json.loads(docker('inspect', 'singux-runtime-rcoder-1'))[0]
            if current['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(2)
        else:
            raise RuntimeError('RCoder restart health timeout')
        assert current['Id'] == rcoder['Id'] and current['Mounts'] == rcoder['Mounts']
        assert current['NetworkSettings']['Networks'].keys() == rcoder['NetworkSettings']['Networks'].keys()
        mounted = subprocess.check_output(['docker', 'exec', 'singux-runtime-rcoder-1', 'cat', destination])
        assert hashlib.sha256(mounted).digest() == hashlib.sha256(updated).digest()
        assert sorted(before_ids) == sorted(docker('ps', '-q', '--no-trunc').splitlines())
    except Exception:
        CONFIG.write_bytes(before)
        docker('restart', 'singux-runtime-rcoder-1')
        raise
    result = {'status': 'DESKTOP_READINESS_PATCHED', 'image': NEW,
              'imageId': json.loads(docker('image', 'inspect', NEW))[0]['Id'],
              'launcherSha256': hashlib.sha256(launcher.read_bytes()).hexdigest(),
              'sourceChanged': False, 'businessDatabaseChanged': False,
              'runtimeContainerIdPreserved': True, 'businessVerified': False}
    record.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
