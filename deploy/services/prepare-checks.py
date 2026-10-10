"""Create only named disposable local fixtures, never real user projects."""
import json
import urllib.error
import urllib.request


def request(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as response:
        result = json.load(response)
    if result.get('success') is False:
        raise RuntimeError(str(result.get('message')))
    return result


for project, context in [('singux-service-check-20261009', {}),
                         ('singux-isolated-check', {'tenantId': '1', 'spaceId': '1', 'isolationType': 'project'})]:
    try:
        request('http://127.0.0.1:16000/api/project/create-project',
                {'projectId': project, 'templateType': 'react', **context})
    except urllib.error.HTTPError as error:
        result = json.load(error)
        if 'already exists' not in str(result.get('error', {}).get('message', '')):
            raise
    body = {'user_id': 'singux-local-check', 'project_id': project, 'service_type': 'web-agent-runner'}
    if context:
        body.update(tenant_id='1', space_id='1', isolation_type='project', pod_id=project)
    request('http://127.0.0.1:8086/computer/pod/ensure', body)
request('http://127.0.0.1:8086/computer/pod/ensure', {
    'user_id': 'singux-local-desktop-check', 'project_id': 'singux-desktop-check',
    'service_type': 'computer-agent-runner'})
request('http://127.0.0.1:16000/api/build/start-dev?projectId=singux-service-check-20261009')
print('LOCAL_FIXTURES_READY')
