// Emits a read-only query as base64 for transport; never emits passwords.
const x=require('xlsx');
const c=require('../desktop/core.cjs');
const path=require('node:path');
const dir=process.argv[2];
const read=f=>{const w=x.readFile(path.join(dir,f));return x.utils.sheet_to_json(w.Sheets[w.SheetNames[0]],{header:1,defval:'',raw:false});};
const rows=read('Template (1).xls'), exported=read('singux-accounts-32b6c159.xlsx').slice(1);
const options={schoolCode:'cdut',usernameMode:'schoolIdentifier',passwordMode:'schoolIdentifier'};
const people=c.deduplicate(c.normalize(c.extract({id:'audit',name:'audit',file:'template',rows},options),options));
const roster=people.map(p=>({raw:p.originalUid,uid:p.uid,login:p.userName,name:p.nickName,phone:p.phone,email:p.email,previous:exported.find(r=>r[1]===p.userName)?.[4]||'missing'}));
const hex=Buffer.from(JSON.stringify(roster)).toString('hex');
const sql=`SET NAMES utf8mb4;
START TRANSACTION READ ONLY;
WITH roster AS (SELECT * FROM JSON_TABLE(CONVERT(0x${hex} USING utf8mb4),'$[*]' COLUMNS(rawid VARCHAR(128) PATH '$.raw', uid VARCHAR(128) PATH '$.uid', login VARCHAR(64) PATH '$.login', name VARCHAR(64) PATH '$.name', phone VARCHAR(64) PATH '$.phone', email VARCHAR(255) PATH '$.email', previous VARCHAR(64) PATH '$.previous')) j),
matched AS (SELECT r.login,r.previous,COUNT(u.id) hits,
SUM(u.user_name=r.login) target_login,
SUM(u.user_name=r.login AND u.nick_name=r.name AND ((r.phone<>'' AND u.phone=r.phone) OR (r.email<>'' AND LOWER(u.email)=LOWER(r.email)))) corroborated,
SUM(u.role='Admin' OR u.status<>'Enabled' OR u._tenant_id<>1) protected,
SUM(u.uid=r.uid OR (u.uid=r.rawid AND u.nick_name=r.name AND ((r.phone<>'' AND u.phone=r.phone) OR (r.email<>'' AND LOWER(u.email)=LOWER(r.email))))) old_match
FROM roster r LEFT JOIN agent_platform.user u ON u.uid=r.uid OR u.uid=r.rawid OR u.user_name=r.login OR (r.phone<>'' AND u.phone=r.phone) OR (r.email<>'' AND LOWER(u.email)=LOWER(r.email)) GROUP BY r.login,r.previous)
SELECT previous,CASE WHEN hits=0 THEN 'NOT_FOUND' WHEN hits>1 THEN 'MULTIPLE_ACCOUNTS' WHEN protected>0 THEN 'PROTECTED' WHEN old_match>0 THEN 'OLD_RULE_MATCH' WHEN corroborated>0 THEN 'NEW_RULE_MATCH' WHEN target_login>0 THEN 'LOGIN_MATCH_NEEDS_REVIEW' ELSE 'CONTACT_ONLY_NEEDS_REVIEW' END category,COUNT(*) accounts FROM matched GROUP BY previous,category ORDER BY previous,category;
COMMIT;`;
process.stdout.write(Buffer.from(sql).toString('base64'));
