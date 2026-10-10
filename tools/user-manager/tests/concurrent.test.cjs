const {test}=require('node:test');
const assert=require('node:assert/strict');
const {runTask}=require('../desktop/queue.cjs');
const {findExisting,ApiError}=require('../desktop/api.cjs');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function batch(n=8){return {concurrency:3,intervalMs:250,scope:'single',entries:Array.from({length:n},(_,i)=>({status:'pending',person:{id:String(i),uid:'school:'+i,userName:'school'+i,nickName:'Person',phone:'1380013'+String(i).padStart(4,'0'),email:`person${i}@example.invalid`,sources:[]}}))};}
test('bounded workers share one snapshot and global pacing; persisted before writes',async()=>{
 const t=batch();let active=0,peak=0,reads=0,posts=0,saves=0;const delays=[];
 await runTask(t,{users:async()=>{reads++;return [];},request:async(_r,p)=>{
  assert.ok(saves>0);assert.equal(t.entries.find(e=>e.person.uid===p.uid).status,'sending');
  active++;peak=Math.max(peak,active);await wait(10);active--;return String(++posts);
 }},async()=>{saves++;},()=>false,async ms=>{delays.push(ms);});
 assert.equal(t.status,'completed');assert.equal(reads,1);assert.equal(posts,8);assert.equal(peak,3);
 assert.equal(delays.length,7);assert.ok(delays.every(ms=>ms>=250));
});
test('pause drains admitted requests and does not admit more',async()=>{
 const t=batch();let stop=false,posts=0;
 await runTask(t,{users:async()=>[],request:async()=>{posts++;stop=true;await wait(5);return '11';}},async()=>{},()=>stop,async()=>{});
 assert.equal(t.status,'paused');assert.ok(posts<=3);assert.ok(t.entries.some(e=>e.status==='pending'));
});
test('network uncertainty isolates the row and never replays unknown POST',async()=>{
 const t=batch(1);let posts=0;
 const api={users:async()=>[],request:async()=>{posts++;throw new ApiError('NETWORK','timeout');}};
 await runTask(t,api,async()=>{},()=>false,async()=>{});
 assert.equal(t.entries[0].status,'unknown');assert.equal(t.status,'partial');
 await runTask(t,api,async()=>{},()=>false,async()=>{});assert.equal(posts,1);
});
test('duplicate batch identity is never concurrently created twice',async()=>{
 const t=batch(2);t.entries[1].person.phone=t.entries[0].person.phone;let posts=0;
 await runTask(t,{users:async()=>[],request:async()=>String(++posts)},async()=>{},()=>false,async()=>{});
 assert.equal(posts,1);assert.equal(t.entries[1].status,'conflict');
});
test('concurrent persistence failure stops writes and waits for workers',async()=>{
 const t=batch();let saves=0,posts=0;
 await assert.rejects(()=>runTask(t,{users:async()=>[],request:async()=>{posts++;return '1';}},async()=>{if(++saves>1)throw Error('disk full');},()=>false,async()=>{}));
 assert.equal(posts,0);
});
test('conflict identifies differing login and uid without merging',()=>{
 const row=batch(1).entries[0].person;
 assert.throws(()=>findExisting(row,[{...row,id:'19',userName:'oldname',uid:'old-id'}]),e=>e.code==='CONFLICT'&&e.message.includes('oldname')&&e.message.includes('学工号标识'));
});
