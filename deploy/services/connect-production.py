"""Register private sandbox services, then change only existing backend service URLs."""
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
DEPLOY = Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')


def run(args, out=None):
    result = subprocess.run(args, stdout=out if out is not None else subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:3]))
    return result.stdout.decode().strip() if out is None else ''


def main():
    os.umask(0o077)
    result = json.loads((HERE / 'deployment-result.json').read_text())
    if result['status'] != 'SERVICES_DEPLOYED':
        raise RuntimeError('Services not verified')
    backup = Path(result['backup'])
    backend = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
    files = backend['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
    if files != [str(DEPLOY / 'compose.json'), str(DEPLOY / 'compose.mcp.json')]:
        raise RuntimeError('Unexpected current Compose files; review required')
    if (DEPLOY / 'compose.runtime.json').exists():
        raise RuntimeError('Existing runtime override; review required')
    base_cmd = ['docker', 'compose', '-p', 'singux', '--env-file', str(DEPLOY / '.env')]
    for file in files:
        base_cmd += ['-f', file]
    for file in [*files, str(DEPLOY / '.env')]:
        shutil.copy2(file, backup / Path(file).name)
    with (backup / 'database-before.sql').open('wb') as out:
        run(['docker', 'exec', 'singux-mysql-1', 'sh', '-c',
             'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --routines --events --triggers --no-tablespaces agent_platform'], out)
    print('CONFIG_AND_SQL_BACKUP_OK', flush=True)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = ''

    def api(path, payload=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request('http://127.0.0.1:8080' + path, headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None)
        with opener.open(req, timeout=90) as response:
            response_data = json.load(response)
        if response_data.get('code') != '0000':
            raise RuntimeError('Management API rejected ' + path + ' code=' + str(response_data.get('code')))
        return response_data.get('data')

    password = os.environ.pop('SINGUX_ADMIN_PASSWORD')
    login = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})
    password = None
    token = login['token']
    entries = api('/api/system/sandbox/config/global/list') or []
    (backup / 'sandbox.before.json').write_text(json.dumps(entries))
    keys = ['singux-production-agent', 'singux-production-page']
    if any(item.get('configKey') in keys for item in entries):
        raise RuntimeError('Existing production registration; review required')
    override = DEPLOY / 'compose.runtime.json'
    next_cmd = base_cmd + ['-f', str(override)]
    created = []
    try:
        for kind, key in zip(['Agent', 'PageApp'], keys):
            dto = {'scope': 'GLOBAL', 'name': 'Singu X production ' + kind, 'configKey': key,
                   'type': kind, 'isActive': False, 'isolation': 'Project', 'maxAgentCount': 1,
                   'configValue': {'hostWithScheme': 'http://singux-service-gateway',
                                  'agentPort': 8090, 'vncPort': 8088, 'fileServerPort': 60000,
                                  'apiKey': (HERE / 'service-key').read_text(), 'maxUsers': 1}}
            api('/api/system/sandbox/config/create', dto)
            found = next(item for item in api('/api/system/sandbox/config/global/list') if item.get('configKey') == key)
            created.append(found['id'])
            api('/api/system/sandbox/config/test/' + str(found['id']))
        override.write_text(json.dumps({'services': {'backend': {'image': backend['Image'], 'environment': {
            'BUILD_SERVER_URL': 'http://singux-file-service:60000/api',
            'AI_AGENT_URL': 'http://singux-service-gateway:8090',
            'DOCKER_PROXY_URL': 'http://singux-service-gateway:8088'}}}}, indent=2))
        run(next_cmd + ['config', '-q'])
        print('BACKEND_URL_SWITCH', flush=True)
        run(next_cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'backend'])
        for _ in range(90):
            current = json.loads(run(['docker', 'inspect', 'singux-backend-1']))[0]
            if current['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(3)
        else:
            raise RuntimeError('Backend health timeout')
        assert current['Image'] == backend['Image']
        assert current['Mounts'] == backend['Mounts']
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-t'])
        run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        api('/api/tenant/config')
        for cid in created:
            api('/api/system/sandbox/config/test/' + str(cid))
        for cid in created:
            api('/api/system/sandbox/config/toggle/' + str(cid), {})
        for original in json.loads((backup / 'containers.before.json').read_text()):
            if original['Name'] == '/singux-backend-1':
                continue
            present = json.loads(run(['docker', 'inspect', original['Name']]))[0]
            assert present['Id'] == original['Id'] and present['Image'] == original['Image'] and present['State']['Running']
        result.update(backendConnected=True, sandboxConfigIds=created, status='PLATFORM_CONNECTED',
                      existingContainersUnchanged=False, backendContainerRecreated=True,
                      backendImageAndMountsPreserved=True, existingInfrastructureContainersUnchanged=True,
                      capacityNote='maxUsers=1 per service; advisory status-based limit, not atomic global admission')
        (HERE / 'deployment-result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except BaseException:
        if override.exists():
            run(base_cmd + ['up', '-d', '--no-deps', '--pull', 'never', 'backend'])
            override.rename(backup / 'failed.compose.runtime.json')
            run(['docker', 'exec', 'singux-frontend-1', 'nginx', '-s', 'reload'])
        for cid in created:
            try:
                api('/api/system/sandbox/config/delete/' + str(cid), {})
            except Exception:
                print('REGISTRATION_ROLLBACK_REQUIRES_REVIEW id=' + str(cid), flush=True)
        raise


if __name__ == '__main__':
    main()
