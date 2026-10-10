"""Normal-login target web-app fixture; no publication or model invocation."""
import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

ROOT = Path('/data/singux-migration-20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retry-cleaned-failure', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assert socket.gethostname() == 'vm133'
    backend = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-backend-1']))[0]
    assert backend['Config']['Labels']['com.docker.compose.project.config_files'] == str(ROOT / 'compose.app.test.json')
    assert set(backend['NetworkSettings']['Networks']) == {'singux_default'}
    output = ROOT / 'authenticated-webapp-verification.json'
    if output.exists():
        previous = json.loads(output.read_text())
        if previous['status'] == 'AUTHENTICATED_WEBAPP_VERIFIED':
            print(json.dumps(previous)); return
        assert args.retry_cleaned_failure and previous['fixturesRemoved']
        output.rename(ROOT / ('authenticated-webapp-failed-' + uuid.uuid4().hex + '.json'))
    token = ''
    project_id = None
    start_attempted = False
    stage = 'login'
    result = {'status': 'AUTHENTICATED_WEBAPP_TESTING', 'checks': [],
              'sourceChanged': False, 'modelInvoked': False, 'published': False,
              'publicAccessVerified': False}

    def save():
        output.write_text(json.dumps(result, indent=2))

    def raw(path, body=None):
        request = urllib.request.Request('http://127.0.0.1:8080' + path,
                    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
                    data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(request, timeout=240) as response:
            return response.read()

    def api(path, body=None):
        record = json.loads(raw(path, body))
        if record.get('code') != '0000':
            result['lastBusinessCode'] = str(record.get('code'))
            raise RuntimeError('Business API rejected')
        return record.get('data')

    try:
        credentials = json.load(sys.stdin)
        token = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': credentials.pop('password')})['token']
        spaces = [s for s in api('/api/space/list') if s.get('type') == 'Personal']
        assert len(spaces) == 1
        stage = 'project-create'
        created = api('/api/custom-page/create', {'spaceId': spaces[0]['id'], 'templateType': 'react',
                      'projectName': 'migration-webapp-' + uuid.uuid4().hex[:12],
                      'projectDesc': 'Temporary migration web-app verification', 'icon': ''})
        project_id = created['projectId']
        assert isinstance(project_id, int)
        result['fixtureProjectId'] = project_id
        result['checks'].append('authenticated-template-project-created')
        save()
        stage = 'project-read'
        info = api('/api/custom-page/get-project-info?projectId=' + str(project_id))
        assert info
        content = api('/api/custom-page/get-project-content?projectId=' + str(project_id))
        assert content
        result['checks'].append('authenticated-project-info-and-content')
        stage = 'start-dev'
        start_attempted = True
        dev = api('/api/custom-page/start-dev', {'projectId': project_id})
        preview = dev.get('devServerUrl')
        assert preview and isinstance(preview, str)
        parsed = urllib.parse.urlsplit(preview)
        assert not parsed.scheme and not parsed.netloc, 'Unexpected external preview; do not access'
        result['checks'].append('authenticated-dev-server-started')
        stage = 'preview-read'
        assert b'<html' in raw(preview).lower()
        result['checks'].append('authenticated-preview-html')
        stage = 'keep-alive'
        alive = api('/api/custom-page/keepalive', {'projectId': project_id})
        assert alive and alive.get('devServerUrl') == preview
        result['checks'].append('authenticated-dev-keep-alive')
        result['status'] = 'AUTHENTICATED_WEBAPP_VERIFIED'
    except Exception as error:
        result.update(status='AUTHENTICATED_WEBAPP_FAILED', failureStage=stage, errorType=type(error).__name__)
    finally:
        errors = []
        if project_id is not None:
            if start_attempted:
                # The file service can report failure before SIGTERM exit completes.
                stopped = False
                for attempt in range(3):
                    try:
                        api('/api/custom-page/stop-dev', {'projectId': project_id})
                        stopped = True
                        result['stopAttempts'] = attempt + 1
                        break
                    except Exception:
                        time.sleep(1)
                if not stopped:
                    errors.append('fixture-dev-stop')
            try:
                api('/api/custom-page/delete-project', {'projectId': project_id})
            except Exception:
                errors.append('fixture-project-delete')
        result['fixturesRemoved'] = not errors
        result['cleanupErrors'] = errors
        if errors:
            result['status'] = 'AUTHENTICATED_WEBAPP_FAILED'
        result['completedUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(json.dumps(result))


if __name__ == '__main__':
    main()
