const {test}=require('node:test');
const assert=require('node:assert/strict');
const {resolveUpdate,snapshot}=require('../desktop/update-policy.cjs');
const {runTask}=require('../desktop/queue.cjs');
const {accountRows}=require('../desktop/account-report.cjs');
const person={id:'row',originalUid:'00001',uid:'cdut:person:00001',userName:'cdut00001',nickName:'Demo',phone:'13800138000',email:'demo@example.invalid',sources:[]};
const user={id:'12',uid:'00001',userName:'user00001',nickName:'Demo',phone:'',email:'demo@example.invalid',role:'User',status:'Enabled'};
const noWait=async()=>{};
test('migrated email registration is matched without rewriting its uid',()=>{
 const migrated={...user,uid:'registration-id',userName:person.userName};
 assert.equal(resolveUpdate(person,[migrated]).id,'12');
 for(const patch of [{nickName:'Other'},{email:''},{userName:'another'},{role:'Admin'},{status:'Disabled'}])assert.throws(()=>resolveUpdate(person,[{...migrated,...patch}]),/未能|仅允许/);
 assert.throws(()=>resolveUpdate(person,[migrated,{...user,id:'13'}]),/多个/);
});
function task(){return {schoolCode:'cdut',passwordMode:'schoolIdentifier',updateExisting:true,concurrency:3,intervalMs:500,entries:[{person:{...person},approvedTarget:snapshot(user),status:'pending'}]};}
test('legacy raw uid matches only with name and contact corroboration',()=>{
 assert.equal(resolveUpdate(person,[user]).id,'12');
 for(const patch of [{nickName:'Other'},{email:''},{role:'Admin'},{status:'Disabled'},{role:undefined},{uid:'other'}])assert.throws(()=>resolveUpdate(person,[{...user,...patch}]),/不能|仅允许|未能/);
 assert.throws(()=>resolveUpdate(person,[user,{...user,id:'13'}]),/多个/);
});
test('existing user updated by ID, preserving uid and exporting confirmed reset password',async()=>{
 const t=task();let current={...user},body,posts=0;
 await runTask(t,{users:async()=>[{...current}],request:async(route,data)=>{
  if(route.includes('/detail?'))return {...current};
  assert.equal(route,'/api/v1/system/user/12/update');assert.equal(t.entries[0].status,'sending');body=data;posts++;current={...current,...data};return null;
 }},noWait,()=>false,noWait);
 assert.equal(t.status,'completed');assert.equal(posts,1);assert.equal(t.entries[0].status,'updated');
 assert.equal(body.password,'cdut00001');assert.equal(body.userName,'cdut00001');assert.equal(body.role,'User');assert.ok(!('uid' in body));
 assert.equal(accountRows(t,true)[0].password,'cdut00001');assert.equal(current.uid,'00001');
});
test('successful no-op response is not accepted, unknown update never replays',async()=>{
 const t=task();let posts=0;
 const api={users:async()=>[{...user}],request:async(route)=>{if(route.includes('/detail?'))return {...user};posts++;return null;}};
 await runTask(t,api,noWait,()=>false,noWait);assert.equal(t.entries[0].status,'unknown');assert.equal(accountRows(t,true)[0].password,'');
 await runTask(t,api,noWait,()=>false,noWait);assert.equal(posts,1);assert.equal(t.entries[0].status,'unknown');
});
test('changed or deleted approved target is never updated or recreated',async()=>{
 for(const users of [[],[{...user,userName:'changed'}]]){
  const t=task();let calls=0;
  await runTask(t,{users:async()=>users,request:async()=>{calls++;}},noWait,()=>false,noWait);
  assert.equal(calls,0);assert.equal(t.entries[0].status,'conflict');
 }
});
test('new users use school identifier password and ordinary role',async()=>{
 const t=task();t.entries[0].approvedTarget=null;let body;
 await runTask(t,{users:async()=>[],request:async(route,data)=>{assert.equal(route,'/api/v1/system/user/add');body=data;return '13';}},noWait,()=>false,noWait);
 assert.equal(body.password,'cdut00001');assert.equal(body.role,'User');assert.equal(t.entries[0].status,'done');
});
test('credentials export hides a failed password reset even if account exists',()=>{
 const t=task();Object.assign(t.entries[0],{operation:'update',password:'cdut00001',userId:'12',status:'unknown'});
 assert.equal(accountRows(t,true)[0].password,'');
});
