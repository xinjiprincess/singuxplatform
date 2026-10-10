"""Pinned diagnostics; only --repair-skills writes reviewed, backed-up publication flags."""
import base64
import hashlib
import json
import os
import re
import shlex
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tmp' / 'ssh-diagnostic-libs'))
import paramiko

PIN = 'SHA256:j9wQITtHH7ZeO7fVw7wgQUzj6JaMiHgmNOg0+S2ttxU'

class PinnedKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        actual = 'SHA256:' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
        if key.get_name() != 'ssh-ed25519' or actual != PIN:
            raise paramiko.SSHException('Server host key does not match the verified fingerprint')

def redact(value):
    value = re.sub(r'(?i)(Bearer\s+)[^\s"\']+', r'\1[REDACTED]', value)
    value = re.sub(r'(?i)("(?:password|key|apiKey|token|accessToken)"\s*:\s*)"[^"]*"', r'\1"[REDACTED]"', value)
    return re.sub(r'\b(?:ak|sk)-[A-Za-z0-9_-]+', '[REDACTED]', value)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(PinnedKey())
password = os.environ.pop('SINGUX_SSH_PASSWORD')
client.connect('43.136.175.19', username='root', password=password,
               timeout=20, auth_timeout=20, banner_timeout=20, look_for_keys=False, allow_agent=False)
password = None

def run(label, command, input_text=None):
    print('\n## ' + label, flush=True)
    stdin, stdout, stderr = client.exec_command(command, timeout=60)
    if input_text is not None:
        stdin.write(input_text)
        stdin.flush()
        stdin.channel.shutdown_write()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(redact(out[-18000:]), flush=True)
    if err:
        print(redact(err[-1500:]), flush=True)
    return out

def sql(label, statement):
    command = "docker exec -i singux-mysql-1 sh -c " + shlex.quote(
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B --default-character-set=utf8mb4 agent_platform')
    return run(label, command, 'START TRANSACTION READ ONLY;\n' + statement + '\nCOMMIT;\n')

try:
    if '--repair-skills' in sys.argv:
        predicate = "_tenant_id=1 AND target_type='Skill' AND target_id BETWEEN 5 AND 11 AND space_id IN (24,32)"
        raw = sql('Scoped skill snapshot', "SELECT JSON_OBJECT('id',id,'targetId',target_id,'spaceId',space_id,'scope',scope,'onlyTemplate',only_template,'modified',modified,'name',name) FROM published WHERE " + predicate + " ORDER BY id;")
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        expected_names = {'work-record-understanding','state-evidence-verification','material-smart-archiving','smart-retrospective','organizational-experience-deposition','organizational-memory-qa','personal-growth-deposition'}
        if len(rows) != 14 or {row['name'] for row in rows} != expected_names or any(row['scope'] != 'Space' for row in rows):
            raise RuntimeError('Published skill snapshot no longer matches the reviewed scope')
        folder = Path(__file__).resolve().parents[1] / 'outputs' / ('skill-recovery-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        folder.mkdir(parents=True, exist_ok=False)
        (folder / 'published-flags.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        ids = ','.join(str(int(row['id'])) for row in rows)
        rollback = 'START TRANSACTION;\n' + '\n'.join('UPDATE published SET only_template={} WHERE id={} AND {};'.format(int(row['onlyTemplate']),int(row['id']),predicate) for row in rows) + '\nCOMMIT;\n'
        (folder / 'rollback.sql').write_text(rollback, encoding='ascii')
        command = "docker exec -i singux-mysql-1 sh -c " + shlex.quote('MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B --default-character-set=utf8mb4 agent_platform')
        run('Enable reviewed skills for direct selection; preserve scope and access control', command,
            'START TRANSACTION; UPDATE published SET only_template=0 WHERE ' + predicate + ' AND id IN (' + ids + ') AND only_template=1; SELECT ROW_COUNT(); COMMIT;\n')
        result = sql('Post-change verification', 'SELECT COUNT(*) FROM published WHERE ' + predicate + ' AND only_template=0;').strip()
        if result != '14':
            raise RuntimeError('Unexpected post-change count; review saved snapshot')
        print('SKILL_REPAIR_OK backup=' + str(folder))
        sys.exit(0)
    if '--probe-school' in sys.argv:
        probe = '''import json, subprocess, urllib.request, urllib.error
command = ['docker','exec','-i','singux-mysql-1','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B --default-character-set=utf8mb4 agent_platform']
row = subprocess.check_output(command,input=b'START TRANSACTION READ ONLY; SELECT model,api_info FROM model_config WHERE id=26; COMMIT;').decode().strip()
model, endpoints = row.split('\\t',1)
endpoint = json.loads(endpoints)[0]
url = endpoint['url'].strip()
if url != 'http://61.188.36.255:18000/maas/v1': raise RuntimeError('Unexpected configured endpoint')
headers = {'Content-Type':'application/json'}
if endpoint.get('key'): headers['Authorization'] = 'Bearer ' + endpoint['key']
payload = json.dumps({'model':model,'messages':[{'role':'user','content':'Reply with OK'}],'max_tokens':16,'stream':False}).encode()
try:
    with urllib.request.urlopen(urllib.request.Request(url+'/chat/completions',data=payload,headers=headers),timeout=40) as response:
        data = json.load(response)
        text = (data.get('choices') or [{}])[0].get('message',{}).get('content')
        print(json.dumps({'modelId':26,'status':response.status,'hasOutput':bool(text),'outputLength':len(text or '')}))
except urllib.error.HTTPError as e: print(json.dumps({'modelId':26,'status':e.code,'hasOutput':False}))
except Exception as e: print(json.dumps({'modelId':26,'errorType':type(e).__name__}))
'''
        run('Configured school model probe (no credentials or generated text printed)', 'python3 -', probe)
        sys.exit(0)
    run('Containers', "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'")
    run('Service ports', "ss -lnt | grep -E ':80 |:443 |:8080 |:8086 |:8088 |:60000 |:8000 |:18020 '")
    # Filter before printing: never expose the complete container environment.
    _, stdout, _ = client.exec_command("docker inspect singux-backend-1 --format '{{json .Config.Env}}'", timeout=20)
    environment = json.loads(stdout.read())
    allowed = {'BUILD_SERVER_URL', 'AI_AGENT_URL', 'DOCKER_PROXY_URL', 'PLATFORM_MEMBERSHIP_ENABLED'}
    print('\n## Backend service endpoints\n' + redact('\n'.join(item for item in environment if item.split('=', 1)[0] in allowed)))
    run('Elasticsearch plugins', "docker exec singux-elasticsearch-1 curl -fsS 'http://127.0.0.1:9200/_nodes/plugins?filter_path=nodes.*.plugins.name,nodes.*.version'")
    run('Recent failure summaries', "docker exec singux-backend-1 sh -c " + shlex.quote(
        "tail -n 20000 /app/logs/app.log | grep -E 'Agent computer not configured|illegal_argument_exception|ik_max_word|403 Forbidden|Failed to batch build indexes' | grep -v -E 'LogRecordPrint-content|^Request |^Response ' | tail -n 20"))
    tables = sql('Relevant tables', "SHOW TABLES;")
    selected = [name for name in tables.splitlines() if re.fullmatch(r'[a-zA-Z0-9_]+', name)
                and name in ('knowledge_task', 'knowledge_task_history', 'knowledge_config', 'model_config')]
    for table in selected[:16]:
        sql('Schema: ' + table, 'SHOW COLUMNS FROM `' + table + '`;')
    sql('Sandbox availability', "SELECT scope,type,is_active,COUNT(*) FROM sandbox_config GROUP BY scope,type,is_active;")
    sql('Imported skills', "SELECT id,name,_tenant_id,space_id,publish_status,ext FROM skill_config WHERE yn=1 AND (name LIKE 'organizational-%' OR name IN ('smart-retrospective','work-record-understanding','state-evidence-verification','personal-growth-deposition','material-smart-archiving'));")
    sql('Published skill visibility', "SELECT target_id,name,_tenant_id,space_id,scope,only_template,access_control,ext FROM published WHERE target_type='Skill' ORDER BY modified DESC LIMIT 20;")
    sql('Knowledge model selection', "SELECT id,space_id,chat_model_id,embedding_model_id,fulltext_sync_status FROM knowledge_config WHERE yn=1 ORDER BY modified DESC LIMIT 20;")
    sql('Model endpoints without credentials', "SELECT m.id,m.name,m.model,m.type,m.enabled,j.url FROM model_config m JOIN JSON_TABLE(m.api_info,'$[*]' COLUMNS(url VARCHAR(512) PATH '$.url')) j ORDER BY m.id;")
    sql('Recent task status', "SELECT id,kb_id,doc_id,type,status,retry_cnt,modified,CASE WHEN result LIKE '%403%' THEN 'MODEL_HTTP_403' WHEN result LIKE '%ik_max_word%' OR result LIKE '%ik_smart%' THEN 'MISSING_IK_ANALYZER' WHEN result LIKE '%全文%' THEN 'FULLTEXT_ERROR' ELSE 'OTHER' END FROM knowledge_task WHERE yn=1 ORDER BY modified DESC LIMIT 20;")
    sql('Historical task status', "SELECT id,kb_id,doc_id,type,status,retry_cnt,modified,CASE WHEN result LIKE '%403%' THEN 'MODEL_HTTP_403' WHEN result LIKE '%ik_max_word%' OR result LIKE '%ik_smart%' THEN 'MISSING_IK_ANALYZER' WHEN result LIKE '%全文%' THEN 'FULLTEXT_ERROR' ELSE 'OTHER' END FROM knowledge_task_history WHERE yn=1 ORDER BY modified DESC LIMIT 20;")
finally:
    client.close()
