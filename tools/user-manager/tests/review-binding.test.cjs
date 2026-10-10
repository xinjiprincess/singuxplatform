const {test}=require('node:test');
const assert=require('node:assert/strict');
const {resolveUpdate,personIdentity,snapshot,updateAccount}=require('../desktop/update-policy.cjs');
const row={uid:'cdut:person:001',originalUid:'001',userName:'cdut001',nickName:'Student',phone:'13800138000',email:'student@example.invalid'};
const user={id:'20',uid:'registered',userName:'old',nickName:'Nickname',phone:'',email:row.email,role:'User',status:'Enabled'};
const binding=()=>({person:personIdentity(row),target:snapshot(user),reason:'Reviewed school record'});
test('contact-only user requires explicit binding; binding supports original and updated snapshots',()=>{
 assert.throws(()=>resolveUpdate(row,[user]),/未能/);
 assert.equal(resolveUpdate(row,[user],binding()).id,'20');
 assert.equal(resolveUpdate(row,[{...user,...row,uid:user.uid}],binding()).id,'20');
});
test('binding rejects changed roster, changed server, multiple users, protected and deleted targets',()=>{
 for(const patch of [{nickName:'Different'},{phone:'13900139000'},{uid:'new'},{id:'21'},{role:'Admin'},{status:'Disabled'}])assert.throws(()=>resolveUpdate(row,[{...user,...patch}],binding()));
 assert.throws(()=>resolveUpdate({...row,originalUid:'002'},[user],binding()));
 assert.throws(()=>resolveUpdate(row,[user,{...user,id:'21'}],binding()));
 assert.throws(()=>resolveUpdate(row,[],binding()));
});
test('approved contact-only update keeps user ID and uid, and checks detail before write',async()=>{
 const entry={person:row,manualBinding:binding(),approvedTarget:snapshot(user),password:'cdut001'};
 let current={...user},posts=0;
 const api={request:async(route,body)=>{if(route.includes('/detail?'))return {...current};assert.equal(route,'/api/v1/system/user/20/update');assert.ok(!('uid' in body));posts++;current={...current,...body};}};
 assert.equal(await updateAccount(entry,[{...user}],{},api,async()=>{}),true);
 assert.equal(posts,1);assert.equal(entry.userId,'20');assert.equal(current.uid,'registered');
});
