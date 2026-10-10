const {test}=require('node:test');const assert=require('node:assert/strict');
const {queryParams,matchRow,runRoles,safeUser}=require('../desktop/user-query.cjs');
const profile={scope:'single'};
test('query encodes username and preserves long string ID',()=>{assert.equal(new URLSearchParams(queryParams({username:'张三+a'})).get('username'),'张三+a');assert.equal(queryParams({id:'9223372036854775807'}),'id=9223372036854775807');assert.throws(()=>queryParams({}));assert.throws(()=>queryParams({id:9223372036854775807}));assert.equal(safeUser({id:1,password:'secret'},profile).password,undefined);});
test('cross-identifier conflicts cannot be batch updated',async()=>{await assert.rejects(matchRow({userDetail:async q=>({id:q.username?1:2,userName:'alice',email:'a@example.com'})},{username:'alice',email:'a@example.com'},profile),/不同用户/);await assert.rejects(matchRow({userDetail:async()=>({id:1,tenantId:2})},{id:'1'},{scope:'tenant',tenantId:'1'}),/租户/);});
test('role only writes and readback catches successful no-op; other rows continue',async()=>{
 const rows=[1,2].map(id=>({userId:String(id),login:'u'+id,currentRole:'User',targetRole:'Admin',status:'ready'}));const roles={1:'User',2:'User'};let writes=0;
 await runRoles({rows},{userDetail:async q=>({id:q.id,userName:'u'+q.id,role:roles[q.id]}),updateUser:async(id,body)=>{assert.deepEqual(body,{role:'Admin'});writes++;if(id==='2')roles[id]='Admin';}},profile,async()=>{},()=>false,async()=>{});
 assert.equal(writes,2);assert.equal(rows[0].status,'unknown');assert.equal(rows[1].status,'done');
});
test('unknown writes are queried without replaying; changed roles block stale plans',async()=>{
 const rows=[{userId:'1',login:'u1',currentRole:'User',targetRole:'Admin',status:'unknown'},{userId:'2',login:'u2',currentRole:'User',targetRole:'User',status:'ready'}];let writes=0;
 await runRoles({rows},{userDetail:async q=>({id:q.id,userName:'u'+q.id,role:'Admin'}),updateUser:async()=>writes++},profile,async()=>{},()=>false,async()=>{});
 assert.equal(writes,0);assert.equal(rows[0].status,'done');assert.equal(rows[1].status,'failed');
});
