"""Pin RCoder's detected main network to the isolated execution bridge."""
import json
import os
from pathlib import Path
import subprocess


def main():
    os.umask(0o077)
    root = Path('/data/singux-update/services-runtime-20261009-r1')
    path = root / 'rcoder.private.json'
    config = json.loads(path.read_text())
    previous = config['docker_config']['network_base_name']
    assert previous in ['singux-runtime', 'singux-execution']
    obj = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-runtime-rcoder-1']))[0]
    assert 'singux-execution' in obj['NetworkSettings']['Networks']
    if previous != 'singux-execution':
        backup = root / 'rcoder.before-network-fix.json'
        assert not backup.exists()
        backup.write_text(path.read_text())
        config['docker_config']['network_base_name'] = 'singux-execution'
        path.write_text(json.dumps(config, indent=2))
    subprocess.run(['docker', 'restart', 'singux-runtime-rcoder-1'], check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'networkBaseName': 'singux-execution', 'sourceChanged': False}))


if __name__ == '__main__':
    main()
