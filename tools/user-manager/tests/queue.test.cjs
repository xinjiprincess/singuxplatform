const {test}=require('node:test');
const assert=require('node:assert/strict');
const {runTask}=require('../desktop/queue.cjs');
const {ApiError,PlatformApi,findExisting}=require('../desktop/api.cjs');
const person={id:'row',uid:'test:person:001',userName:'stu_001',nickName:'Test',phone:'13800138000',email:'test@example.invalid',sources:[]};
const task=()=>({tenantId:'1',intervalMs:0,entries:[{person:{...person},status:'pending'}]});
const noWait=async()=>{};
test('school-phone password is frozen per task and reused by exported credentials',async()=>{
 const t=task();t.passwordMode='schoolPhone';t.schoolCode='cdut';let body;
 await runTask(t,{users:async()=>[],request:async(_route,data)=>{body=data;return '12';}},noWait,()=>false,noWait);
 assert.equal(body.password,'cdut13800138000');
 assert.equal(t.entries[0].password,body.password);
 assert.equal(t.status,'completed');
});
test('phone password applies to new tasks without resetting existing users',async()=>{
  const t=task();t.passwordMode='phone';let body;
  await runTask(t,{users:async()=>[],request:async(_route,data)=>{body=data;return '12';}},noWait,()=>false,noWait);
  assert.equal(body.password,person.phone);assert.equal(t.status,'completed');
  const existing=task();existing.passwordMode='phone';
  await runTask(existing,{users:async()=>[{...person,id:'12'}],request:async()=>{throw Error('must not modify');}},noWait,()=>false,noWait);
  assert.equal(existing.entries[0].password,undefined);assert.equal(existing.entries[0].status,'existing');
});
test('single-tenant mode accepts legacy list without tenant IDs, but blocks mixed scopes',async()=>{
  for(const records of [[],[{id:'1'}]]){
    const api=new PlatformApi({baseUrl:'http://localhost:1234',scope:'single'},'fake',async()=>({ok:true,json:async()=>({code:'0000',data:{records,total:records.length}})}));
    assert.equal((await api.users()).length,records.length);
  }
  const records=[{id:'1',tenantId:1},{id:'2',tenantId:2}];
  const api=new PlatformApi({baseUrl:'http://localhost:1234',scope:'single'},'fake',async()=>({ok:true,json:async()=>({code:'0000',data:{records,total:2}})}));
  await assert.rejects(()=>api.users(),/多个租户/);
});
test('successful creation persists before POST and never imports admin role',async()=>{
  const t=task();let persisted='';let body;
  await runTask(t,{users:async()=>[],request:async(_route,data)=>{assert.equal(persisted,'sending');body=data;return '12';}},async()=>{persisted=t.entries[0].status;},()=>false,noWait);
  assert.equal(t.status,'completed');assert.equal(body.role,'User');assert.ok(body.password.length>=20);
  assert.equal(t.entries[0].confirmedCreation,true);
});
test('exact existing users skip creation; conflicting identities are not overwritten',async()=>{
  const t=task();let posts=0;
  await runTask(t,{users:async()=>[{...person,id:'12'}],request:async()=>{posts++;}},noWait,()=>false,noWait);
  assert.equal(posts,0);assert.equal(t.entries[0].status,'existing');
  assert.throws(()=>findExisting(person,[{...person,id:'12',uid:'other'}]),/身份/);
});
test('unknown POST result is not blindly retried after restart',async()=>{
  const t=task();let posts=0;
  const api={users:async()=>[],request:async()=>{posts++;throw new ApiError('NETWORK','timeout');}};
  await runTask(t,api,noWait,()=>false,noWait);
  assert.equal(t.status,'partial');assert.equal(t.entries[0].status,'unknown');
  await runTask(t,api,noWait,()=>false,noWait);assert.equal(posts,1);
  api.users=async()=>[{...person,id:'12'}];
  await runTask(t,api,noWait,()=>false,noWait);assert.equal(posts,1);assert.equal(t.status,'completed');
  assert.ok(!t.entries[0].confirmedCreation);
});
test('membership failure resumes membership only, not user creation',async()=>{
  const t=task();t.membershipTenantId='2';let posts=0;let fail=true;
  const api={users:async()=>[],request:async(route)=>{if(route.endsWith('/members'))return [];posts++;return '12';},membership:async()=>{if(fail)throw new ApiError('503','unavailable');}};
  await runTask(t,api,noWait,()=>false,noWait);assert.equal(t.entries[0].status,'membership');
  fail=false;await runTask(t,api,noWait,()=>false,noWait);assert.equal(posts,1);assert.equal(t.status,'completed');
});
test('rate limit pauses and never tries another API key',async()=>{
  const t=task();t.entries.push({person:{...person,id:'two',uid:'other'},status:'pending'});let calls=0;
  await runTask(t,{users:async()=>{calls++;throw new ApiError('429','rate limit');}},noWait,()=>false,noWait);
  assert.equal(calls,1);assert.equal(t.status,'paused');assert.equal(t.entries[0].status,'pending');
});
test('cross-tenant, empty lists and lossy numeric IDs are rejected',async()=>{
  for(const records of [[],[{id:'1',tenantId:'2'}],[{id:9007199254740992,tenantId:'1'}]]){
    const api=new PlatformApi({baseUrl:'http://localhost:1234'},'fake',async()=>({ok:true,json:async()=>({code:'0000',data:{records,total:records.length}})}));
    await assert.rejects(()=>api.users('1'));
  }
});
test('separate clients use their selected key and forbid redirects',async()=>{
  const seen=[];
  for(const key of ['test-key-a','test-key-b']){
    const api=new PlatformApi({baseUrl:'http://localhost:1234'},key,async(_url,opts)=>{seen.push(opts.headers.Authorization);assert.equal(opts.redirect,'error');return {ok:true,json:async()=>({code:'0000',data:true})};});
    await api.request('/api/test');
  }
  assert.deepEqual(seen,['Bearer test-key-a','Bearer test-key-b']);
});
test('local persistence failure stops before a mutation',async()=>{
  const t=task();let writes=0;let posts=0;
  await assert.rejects(()=>runTask(t,{users:async()=>[],request:async()=>{posts++;}},async()=>{if(++writes>1)throw Error('disk full');},()=>false,noWait));
  assert.equal(posts,0);
});
