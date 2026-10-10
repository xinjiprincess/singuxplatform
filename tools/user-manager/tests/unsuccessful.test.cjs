const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const XLSX=require('xlsx');
const {runTask}=require('../desktop/queue.cjs');
const {ApiError}=require('../desktop/api.cjs');
const {writeUnsuccessfulWorkbook}=require('../desktop/account-report.cjs');
function task(concurrency){return {concurrency,intervalMs:250,entries:[0,1,2].map(i=>({status:'pending',person:{id:String(i),uid:'u'+i,userName:'school'+i,nickName:'Test',sources:[]}}))};}
for(const concurrency of [1,3])test(`row rejection does not stop other accounts (${concurrency} workers)`,async()=>{
 const t=task(concurrency);let requests=0;
 await runTask(t,{users:async()=>[],request:async(_r,b)=>{requests++;if(b.userName==='school0')throw new ApiError('3000','登录名超过长度限制');return b.userName==='school1'?'11':'12';}},async()=>{},()=>false,async()=>{});
 assert.equal(requests,3);assert.equal(t.status,'partial');assert.deepEqual(t.entries.map(e=>e.status),['unknown','done','done']);
});
test('unresolved old write does not block pending accounts or resend',async()=>{
 const t=task(3);t.entries[0].status='unknown';let requests=0;
 await runTask(t,{users:async()=>[],request:async()=>String(++requests)},async()=>{},()=>false,async()=>{});
 assert.equal(requests,2);assert.deepEqual(t.entries.map(e=>e.status),['unknown','done','done']);
});
test('authorization errors still pause the entire task',async()=>{
 const t=task(1);let requests=0;
 await runTask(t,{users:async()=>[],request:async()=>{requests++;throw new ApiError('403','无权限');}},async()=>{},()=>false,async()=>{});
 assert.equal(requests,1);assert.equal(t.status,'paused');
});
test('unsuccessful workbook excludes successes and secrets, preserves strings and unknown advice',()=>{
 const statuses=['done','existing','failed','conflict','unknown','pending','membership'];
 const t={schoolCode:'cdut',entries:statuses.map(status=>({status,password:'NEVER_EXPORT',person:{nickName:'=SUM(1,2)',userName:'cdut00001',originalUid:'00001',phone:'013800138000',sources:[]}}))};
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'unsuccessful-'));
 try{const file=path.join(dir,'failed.xlsx');writeUnsuccessfulWorkbook(t,file);const sheet=XLSX.readFile(file).Sheets['未成功账号'];const rows=XLSX.utils.sheet_to_json(sheet,{header:1});assert.equal(rows.length,6);assert.equal(sheet.C2.v,'00001');assert.equal(sheet.E2.v,'013800138000');assert.equal(sheet.A2.f,undefined);assert.ok(!JSON.stringify(rows).includes('NEVER_EXPORT'));assert.ok(JSON.stringify(rows).includes('不要直接重新导入'));}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
