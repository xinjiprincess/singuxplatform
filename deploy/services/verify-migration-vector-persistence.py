"""Restart only the target Milvus and recheck exported vectors and searches."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT = Path('/data/singux-migration-20261009')
RESULT = ROOT / 'vector-persistence-verification.json'


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def main():
    os.umask(0o077)
    assert socket.gethostname() == 'vm133', 'Target only'
    before = json.loads((ROOT / 'vector-content-verification.json').read_text())
    assert before['status'] in {'VECTOR_CONTENT_AND_SEARCH_VERIFIED', 'VECTOR_RESTART_PERSISTENCE_VERIFIED'}
    if RESULT.exists():
        state = json.loads(RESULT.read_text())
        if state['status'] == 'VECTOR_RESTART_PERSISTENCE_VERIFIED':
            print('ALREADY_VERIFIED'); return
        assert state['status'] == 'VECTOR_RESTART_VERIFYING', 'Inspect previous failure before retry'
    else:
        container = inspect('singux-milvus-1')
        assert container['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.infra.json')
        assert container['State']['Running']
        assert inspect('singux-backend-1')['State']['Health']['Status'] == 'healthy'
        state = {'status': 'VECTOR_RESTART_VERIFYING', 'containerId': container['Id'],
                 'mounts': container['Mounts'], 'preRestartRows': before['rows'],
                 'sourceChanged': False, 'dataReimported': False}
        RESULT.write_text(json.dumps(state, indent=2))
        subprocess.run(['docker', 'restart', '--time', '60', 'singux-milvus-1'],
                       check=True, stdout=subprocess.DEVNULL, timeout=180)
    current = inspect('singux-milvus-1')
    assert current['Id'] == state['containerId'] and current['Mounts'] == state['mounts']
    ip = current['NetworkSettings']['Networks']['singux_default']['IPAddress']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(100):
        try:
            with opener.open('http://' + ip + ':9091/healthz', timeout=3) as response:
                assert response.status == 200
            break
        except Exception:
            if attempt == 99: raise
            time.sleep(3)
    spec = importlib.util.spec_from_file_location('vectors', ROOT / 'verify-migration-vector-content.py')
    verify = importlib.util.module_from_spec(spec); spec.loader.exec_module(verify)
    verify.main()
    after = json.loads((ROOT / 'vector-content-verification.json').read_text())
    assert after['rows'] == state['preRestartRows'] and after['collections'] == before['collections']
    after['restartPersistenceTested'] = True
    after['status'] = 'VECTOR_RESTART_PERSISTENCE_VERIFIED'
    (ROOT / 'vector-content-verification.json').write_text(json.dumps(after, indent=2))
    record = {'status': 'VECTOR_RESTART_PERSISTENCE_VERIFIED', 'collections': after['collections'],
              'rows': after['rows'], 'filteredSearches': after['filteredSearches'],
              'restartPersistenceTested': True, 'sourceChanged': False, 'dataReimported': False,
              'warnings': after.get('warnings', [])}
    RESULT.write_text(json.dumps(record, indent=2))
    print(json.dumps({key: value for key, value in record.items() if key != 'warnings'}), flush=True)


if __name__ == '__main__':
    main()
