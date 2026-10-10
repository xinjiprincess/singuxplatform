"""Start restored runtime on target without changing the source platform."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
CONFIGS = ROOT / 'business-staged/business-export/configs'
DEST = Path('/data/singux-update/services-runtime-20261009-r1')
WORK = Path('/data/singux-services/workspace')


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    assert p.returncode == 0, 'Command failed: ' + ' '.join(args[:3])
    return p.stdout


def main():
    os.umask(0o077)
    assert json.loads((ROOT / 'vector-restore-result.json').read_text())['status'] == 'VISIBLE_VECTORS_RESTORED'
    assert json.loads(run(['docker', 'network', 'inspect', 'singux_default']))[0]['Internal']
    record_path = ROOT / 'runtime-start-result.json'
    if record_path.exists():
        assert json.loads(record_path.read_text())['status'] == 'RUNTIME_STARTING'
    else:
        assert not DEST.exists() and not WORK.exists()
        source = ROOT / 'workspace-staged/workspace'
        assert source.is_dir() and not source.is_symlink()
        assert source.resolve().is_relative_to(ROOT.resolve())
        assert WORK.parent.resolve().is_relative_to(Path('/data'))
        WORK.parent.mkdir(parents=True, exist_ok=True)
        source.rename(WORK)
        for current, dirs, files in os.walk(WORK, followlinks=False):
            os.chown(current, 1000, 1000)
            for name in dirs + files:
                os.lchown(Path(current) / name, 1000, 1000)
        WORK.chmod(0o750)
        original = CONFIGS / str(DEST).lstrip('/')
        DEST.mkdir(parents=True, mode=0o700)
        for name in ['rcoder.private.json', 'gateway.private.conf']:
            shutil.copyfile(original / name, DEST / name)
            (DEST / name).chmod(0o600)
        config = json.loads((original / 'compose.runtime.json').read_text())
        assert set(config['services']) == {'file-server', 'rcoder', 'gateway'}
        assert config['networks']['platform']['name'] == 'singux_default'
        for service in config['services'].values():
            service['ports'] = []
        (DEST / 'compose.runtime.json').write_text(json.dumps(config, indent=2))
        record_path.write_text(json.dumps({'status': 'RUNTIME_STARTING', 'sourceChanged': False,
                                            'workspace': str(WORK), 'publicPorts': []}, indent=2))
    cmd = ['docker', 'compose', '-p', 'singux-runtime', '-f', str(DEST / 'compose.runtime.json')]
    run(cmd + ['config', '--quiet'])
    run(cmd + ['up', '-d', '--pull', 'never'])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    checks = {}
    for _ in range(80):
        for name, port in [('file-server', 60000), ('rcoder', 8090)]:
            try:
                obj = json.loads(run(['docker', 'inspect', 'singux-runtime-' + name + '-1']))[0]
                ip = obj['NetworkSettings']['Networks']['singux_default']['IPAddress']
                with opener.open('http://' + ip + ':' + str(port) + '/health', timeout=5) as r:
                    checks[name] = r.status == 200
            except Exception:
                checks[name] = False
        if all(checks.values()):
            break
        time.sleep(3)
    assert all(checks.values()), 'Runtime health not ready; preserve services and checkpoint'
    run(['docker', 'exec', 'singux-runtime-gateway-1', 'nginx', '-t'])
    record = {'status': 'RUNTIME_READY', 'checks': checks, 'workspace': str(WORK),
              'sourceChanged': False, 'publicPorts': [], 'realExecutionTested': False}
    record_path.write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
