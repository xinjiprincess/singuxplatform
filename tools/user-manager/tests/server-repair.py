import json, os, urllib.request, time, pathlib

root = pathlib.Path(os.environ['REPAIR_DIR'])
key = os.environ['REPAIR_API_KEY']
rows = json.loads((root / 'roster.json').read_text())
base = 'http://127.0.0.1:8080'

def api(route, body=None):
    req = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as response:
        result = json.load(response)
    if result.get('code') != '0000':
        raise RuntimeError(str(result.get('code')) + ': ' + str(result.get('message')))
    return result.get('data')

def users():
    out = []
    for n in range(1, 101):
        p = api('/api/v1/system/user/list', {'pageNo': n, 'pageSize': 100, 'queryFilter': {}})
        out.extend(p['records'])
        if len(out) >= int(p['total']):
            return out
        time.sleep(0.7)
    raise RuntimeError('Incomplete user list')

def matches(p, all_users):
    return [u for u in all_users if u.get('uid') in [p['uid'], p['originalUid']] or u.get('userName') == p['userName'] or (p['phone'] and u.get('phone') == p['phone']) or (p['email'] and str(u.get('email') or '').lower() == p['email'].lower())]

all_users = users()
results = []
apply = os.environ.get('REPAIR_APPLY') == 'yes'
if apply and (root / 'results.json').exists():
    raise RuntimeError('Previous execution exists; inspect results before any retry')
for p in rows:
    hit = matches(p, all_users)
    category = 'missing' if not hit else 'multiple' if len(hit) > 1 else 'protected' if hit[0].get('role') != 'User' or hit[0].get('status') != 'Enabled' else 'existing'
    result = {'account': p['userName'], 'previous': p['previous'], 'category': category}
    if hit:
        result['userId'] = str(hit[0]['id'])
        result['alreadyTarget'] = hit[0].get('userName') == p['userName']
    results.append(result)
    if not apply or category in ['multiple', 'protected']:
        continue
    try:
        result['result'] = 'in_progress_do_not_retry'
        (root / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        body = {k: p[k] for k in ['userName', 'nickName', 'phone', 'email'] if p.get(k)}
        body.update(password=p['userName'], role='User')
        if hit:
            current = api('/api/v1/system/user/detail?id=' + str(hit[0]['id']))
            if any(current.get(k) != hit[0].get(k) for k in ['id', 'uid', 'userName', 'email', 'phone', 'role', 'status']):
                raise RuntimeError('Target changed')
            # Preserve completed-looking timeout updates; never reset a possibly successful password again.
            if p['previous'] == 'unknown' and all(current.get(k) == body.get(k) for k in ['userName', 'nickName', 'phone', 'email']):
                result['result'] = 'already_matches_password_unverified'
                continue
            api('/api/v1/system/user/' + str(current['id']) + '/update', body)
            uid = current['id']
        else:
            body['uid'] = p['uid']
            uid = api('/api/v1/system/user/add', body)
        after = api('/api/v1/system/user/detail?id=' + str(uid))
        if not after or any(after.get(k) != body.get(k) for k in ['userName', 'nickName', 'phone', 'email', 'role']) or after.get('status') != 'Enabled':
            raise RuntimeError('Readback mismatch')
        if hit and after.get('uid') != current.get('uid'):
            raise RuntimeError('UID changed')
        result.update(result='updated' if hit else 'created', userId=str(uid))
        if hit:
            hit[0].update(after)
        else:
            all_users.append(after)
    except Exception as e:
        result['result'] = 'needs_review'
        result['error'] = str(e).replace(key, '[hidden]')
    finally:
        (root / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        time.sleep(2.2)
(root / ('results.json' if apply else 'audit.json')).write_text(json.dumps(results, ensure_ascii=False, indent=2))
counts = {}
for r in results:
    k = r.get('result', r['category'])
    counts[k] = counts.get(k, 0) + 1
print(json.dumps({'apply': apply, 'counts': counts}))
