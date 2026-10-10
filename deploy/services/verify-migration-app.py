"""Authenticated target reads and one retained upload fixture; password on stdin."""
import http.cookiejar
import json
import hashlib
from pathlib import Path
import sys
import urllib.error
import urllib.request
import urllib.parse

ROOT = Path('/data/singux-migration-20261009')


def main():
    credentials = json.load(sys.stdin)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = ''
    checks = {}

    def api(path, body=None):
        request = urllib.request.Request('http://127.0.0.1:8080' + path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        try:
            with opener.open(request, timeout=45) as response:
                result = json.load(response)
            checks[path] = {'passed': result.get('code') == '0000', 'code': result.get('code')}
            return result.get('data') if checks[path]['passed'] else None
        except urllib.error.HTTPError as error:
            checks[path] = {'passed': False, 'httpStatus': error.code}
            return None

    login = api('/api/user/passwordLogin', {'phoneOrEmail': 'admin', 'password': credentials.pop('password')})
    assert login and login.get('token'), 'Target login failed; no password reset performed'
    token = login['token']
    api('/api/user/getLoginInfo')
    api('/api/tenant/config')
    spaces = api('/api/space/list')
    api('/api/system/sandbox/config/global/list')
    api('/api/system/model/list')
    if spaces:
        space = spaces[0]['id']
        api('/api/knowledge/config/list', {'current': 1, 'pageSize': 20,
            'queryFilter': {'spaceId': space}, 'orders': [], 'filters': []})
        api('/api/mcp/list/' + str(space))
    content = b'Singu X target migration upload roundtrip 20261010\n'
    boundary = 'singux-migration-upload-check-20261010'
    multipart = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; '
                 'filename="migration-target-check.txt"\r\nContent-Type: text/plain\r\n\r\n').encode()
    multipart += content + ('\r\n--' + boundary + '--\r\n').encode()
    request = urllib.request.Request('http://127.0.0.1:8080/api/file/upload', data=multipart,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary,
                 'Authorization': 'Bearer ' + token})
    with opener.open(request, timeout=45) as response:
        uploaded = json.load(response)
    assert uploaded.get('code') == '0000', 'Target fixture upload rejected: ' + str(uploaded.get('code')) + ' ' + str(uploaded.get('message'))[:180]
    parsed = urllib.parse.urlsplit(uploaded['data']['url'])
    assert parsed.path.startswith('/api/f/'), 'Unexpected uploaded file route'
    request = urllib.request.Request('http://127.0.0.1:8080' + parsed.path
        + ('?' + parsed.query if parsed.query else ''), headers={'Authorization': 'Bearer ' + token})
    with opener.open(request, timeout=45) as response:
        actual = response.read()
    assert actual == content, 'Uploaded file roundtrip differs'
    checks['uploadReadback'] = {'passed': True, 'bytes': len(content),
        'sha256': hashlib.sha256(actual).hexdigest(), 'fixtureRetained': True}
    record = {'status': 'APP_AUTH_UPLOAD_CHECKED', 'loginPassed': True, 'checks': checks,
              'sourceChanged': False, 'businessAcceptanceComplete': False,
              'pending': ['real model call blocked by standby egress isolation',
                          'public HTTP reachability', 'authenticated user desktop',
                          'latest source incremental reconciliation']}
    (ROOT / 'app-auth-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
