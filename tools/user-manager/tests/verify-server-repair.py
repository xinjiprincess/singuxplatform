import json, os, pathlib, subprocess
root = pathlib.Path(os.environ['REPAIR_DIR'])
rows = json.loads((root / 'roster.json').read_text())
names = json.dumps([p['userName'] for p in rows]).encode().hex()
sql = """START TRANSACTION READ ONLY;
SELECT JSON_OBJECT('account',u.user_name,'enabled',u.status='Enabled','ordinary',u.role='User','tenant',u._tenant_id,
'initialPasswordMatches',(u.password=u.user_name OR u.password=MD5(CONCAT(MD5(u.user_name),'sxdwq'))))
FROM agent_platform.user u JOIN JSON_TABLE(CONVERT(0x%s USING utf8mb4),'$[*]' COLUMNS(login VARCHAR(64) PATH '$')) j ON u.user_name=j.login;
COMMIT;""" % names
out = subprocess.check_output(['docker','exec','-i','singux-mysql-1','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N --default-character-set=utf8mb4'], input=sql.encode())
records = [json.loads(line) for line in out.decode().splitlines() if line.strip()]
(root / 'verification.json').write_text(json.dumps(records, ensure_ascii=False, indent=2))
print(json.dumps({'expected':len(rows),'found':len(records),'enabledUserTenant1':sum(bool(r['enabled']) and bool(r['ordinary']) and r['tenant']==1 for r in records),'initialPasswordMatches':sum(bool(r['initialPasswordMatches']) for r in records)}))
