"""Register local services using the platform's authorized management API."""
import getpass
import http.cookiejar
import json
import os
import urllib.request


def main():
    base = 'http://127.0.0.1:18093'
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = ''

    def api(path, payload=None):
        headers = {'Content-Type': 'application/json', 'Origin': base}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(base + path, headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None)
        with opener.open(req, timeout=90) as response:
            result = json.load(response)
        if result.get('code') != '0000':
            raise RuntimeError(path + ': ' + str(result.get('message')))
        return result.get('data')

    password = os.environ.pop('SINGUX_LOCAL_ADMIN_PASSWORD', None) or getpass.getpass('Local admin password: ')
    login = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': password})
    password = None
    if login.get('stage') == 'TENANT_SELECTION_REQUIRED':
        login = api('/api/session/tenant/select', {'tenantId': 1})
    token = login['token']
    entries = api('/api/system/sandbox/config/global/list') or []
    for kind, key in [('Agent', 'singux-local-agent'), ('PageApp', 'singux-local-page')]:
        existing = next((item for item in entries if item.get('configKey') == key), None)
        dto = {'scope': 'GLOBAL', 'name': 'Singu X local ' + kind, 'configKey': key,
               'type': kind, 'isActive': True, 'isolation': 'Project', 'maxAgentCount': 4,
               'configValue': {'hostWithScheme': 'http://singux-service-gateway',
                   'agentPort': 8090, 'vncPort': 8088, 'fileServerPort': 60000,
                   'apiKey': '', 'maxUsers': 4}}
        if existing:
            dto['id'] = existing['id']
            api('/api/system/sandbox/config/update', dto)
        else:
            api('/api/system/sandbox/config/create', dto)
    entries = api('/api/system/sandbox/config/global/list')
    for item in entries:
        if item.get('configKey') in ('singux-local-agent', 'singux-local-page'):
            api('/api/system/sandbox/config/test/' + str(item['id']))
            print('REGISTERED_AND_CONNECTED ' + item['configKey'] + ' id=' + str(item['id']))


if __name__ == '__main__':
    main()
