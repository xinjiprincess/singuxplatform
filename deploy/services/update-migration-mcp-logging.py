"""Apply the verified MCP-only patch to the isolated migration backend."""
import copy
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import urllib.request
import zipfile

MIGRATION = Path('/data/singux-migration-20261009')
ROOT = MIGRATION / 'mcp-logging-20261010'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-routing', action='store_true')
    args = parser.parse_args()
    if args.model_routing:
        ROOT = MIGRATION / 'model-routing-20261010'
    prefix = 'MIGRATION_MODEL_ROUTING' if args.model_routing else 'MIGRATION_MCP_LOGGING'
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    helper = module('logging_update', ROOT / 'update-production-logging.py')
    run, inspect = helper.run, helper.inspect
    report = json.loads((ROOT / 'release.json').read_text())
    base_sha = '14c19d06bae8ed464c62aceb5f6cd8bc1c49d9501eeb0fd24f49e7957ad7a581' if args.model_routing else helper.BASE_SHA
    assert report['baselineJarSha256'] == base_sha and report['schemaUnchanged'] is True
    result_path = ROOT / 'result.json'
    backend = inspect('singux-backend-1')
    current_sha = run(['docker', 'exec', backend['Id'], 'sha256sum', '/app/app.jar']).split()[0]
    if result_path.exists():
        existing = json.loads(result_path.read_text())
        assert existing['status'] == prefix + '_UPDATED', 'Review incomplete deployment before retry'
        assert current_sha == report['patchedJarSha256']
        print(json.dumps(existing))
        return
    config_path = MIGRATION / 'compose.app.test.json'
    assert backend['Config']['Labels']['com.docker.compose.project.config_files'] == str(config_path)
    assert backend['Config']['Labels']['com.docker.compose.project'] == 'singux'
    assert backend['State']['Health']['Status'] == 'healthy'
    assert current_sha == base_sha
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    assert json.loads(run(['docker', 'network', 'inspect', 'singux_default']))[0]['Internal']
    queue = module('queue_guard', MIGRATION / 'freeze-migration-queues.py')
    schedule = queue.SCHEDULE
    log_worker = MIGRATION / 'log-worker-result.json'
    if log_worker.exists():
        assert json.loads(log_worker.read_text())['status'] == 'INTERNAL_LOG_WORKER_ENABLED'
        schedule += " AND NOT (bean_id='logApplicationService' AND task_id='logApplicationService')"
    for table, condition in [('schedule_task', schedule), ('pf_retry_data', queue.RETRY)]:
        assert queue.sql('SELECT COUNT(*) FROM ' + table + ' WHERE ' + condition
                         + " AND (lock_time IS NULL OR lock_time<'2099-01-01')") == '0'
    before = config_path.read_bytes()
    config = json.loads(before)
    runtime = ROOT / 'runtime'
    assert not runtime.exists(), 'Preserve existing build and backup; review before retry'
    runtime.mkdir(mode=0o700)
    (ROOT / 'compose.before.json').write_bytes(before)
    (ROOT / 'previous-image.txt').write_text(backend['Image'])
    run(['docker', 'cp', backend['Id'] + ':/app/app.jar', str(ROOT / 'baseline.jar')])
    assert helper.sha(ROOT / 'baseline.jar') == base_sha
    allowed = {'BOOT-INF/lib/app-platform-mcp-application-0.0.1-SNAPSHOT.jar',
               'BOOT-INF/lib/app-platform-mcp-ui-0.0.1-SNAPSHOT.jar'}
    if args.model_routing:
        allowed = {'BOOT-INF/lib/app-platform-agent-core-infra-0.0.1-SNAPSHOT.jar'}
    assert set(report['modules']) == allowed
    replacements = {}
    for name, digest in report['modules'].items():
        path = ROOT / Path(name).name
        assert helper.sha(path) == digest
        replacements[name] = path.read_bytes()
    with zipfile.ZipFile(ROOT / 'baseline.jar') as old, zipfile.ZipFile(runtime / 'app.jar', 'w') as new:
        assert allowed.issubset(old.namelist())
        for item in old.infolist():
            new.writestr(copy.copy(item), replacements.get(item.filename, old.read(item)))
    assert helper.sha(runtime / 'app.jar') == report['patchedJarSha256']
    (runtime / 'Dockerfile').write_text('FROM ' + backend['Image'] + '\nCOPY --chown=app:app app.jar /app/app.jar\n')
    run(['docker', 'build', '--pull=false', '-t', report['image'], str(runtime)])
    preserved = {name: inspect('singux-' + name + '-1')['Id'] for name in
                 ('mysql', 'redis', 'elasticsearch', 'minio', 'etcd', 'milvus', 'mcp-proxy', 'frontend')}
    cmd = ['docker', 'compose', '-p', 'singux', '-f', str(config_path)]
    result_path.write_text(json.dumps({'status': prefix + '_UPDATING', 'sourceChanged': False}))
    try:
        config['services']['backend']['image'] = report['image']
        config_path.write_text(json.dumps(config, indent=2))
        run(cmd + ['config', '--quiet'])
        run(cmd + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        current = inspect('singux-backend-1')
        assert run(['docker', 'exec', current['Id'], 'sha256sum', '/app/app.jar']).split()[0] == report['patchedJarSha256']
        def mounts(item):
            return sorted((m['Type'], m.get('Name', ''), m['Source'], m['Destination'], m['RW']) for m in item['Mounts'])
        assert mounts(current) == mounts(backend)
        assert sorted(current['Config']['Env']) == sorted(backend['Config']['Env'])
        assert current['HostConfig']['Memory'] == backend['HostConfig']['Memory']
        assert set(current['NetworkSettings']['Networks']) == {'singux_default'}
        assert all(inspect('singux-' + name + '-1')['Id'] == value for name, value in preserved.items())
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        with urllib.request.urlopen('http://127.0.0.1:8080/api/tenant/config', timeout=20) as response:
            assert json.load(response)['code'] == '0000'
    except BaseException:
        config_path.write_bytes(before)
        run(cmd + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '600', 'backend'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        result_path.write_text(json.dumps({'status': prefix + '_ROLLED_BACK', 'sourceChanged': False}))
        raise
    result = {'status': prefix + '_UPDATED', 'image': report['image'],
              'jarSha256': report['patchedJarSha256'], 'dataServicesUnchanged': True,
              'sourceChanged': False, 'backendEgressBlocked': True, 'schemaUnchanged': True,
              'businessLogVerification': 'pending', 'backup': str(ROOT)}
    result_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
