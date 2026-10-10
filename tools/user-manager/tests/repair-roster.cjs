const fs=require('node:fs'),x=require('xlsx'),c=require('../desktop/core.cjs');
const file=process.argv[2],report=process.argv[3];
const read=f=>{const w=x.readFile(f);return x.utils.sheet_to_json(w.Sheets[w.SheetNames[0]],{header:1,defval:'',raw:false});};
const rows=read(file),r=read(report),o={schoolCode:'cdut',usernameMode:'schoolIdentifier',passwordMode:'schoolIdentifier',requireBoth:false};
const people=c.deduplicate(c.normalize(c.extract({id:'source',file,name:'registration',rows},o),o));
const entries=r.slice(1).filter(v=>['conflict','unknown','failed'].includes(v[5])).map(v=>{
 const p=people.find(p=>p.userName===v[1]);if(!p||p.errors.length)throw Error('Invalid source row');
 return {uid:p.uid,userName:p.userName,nickName:p.nickName,phone:p.phone,email:p.email,originalUid:p.originalUid,previous:v[5],priorId:v[6]};
});
if(entries.length!==33)throw Error('Unexpected affected count');
process.stdout.write(require('node:zlib').gzipSync(Buffer.from(JSON.stringify(entries))).toString('base64'));
