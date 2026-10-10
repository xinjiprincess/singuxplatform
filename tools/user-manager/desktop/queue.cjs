const crypto = require('node:crypto');
const {findExisting, ApiError, pauses} = require('./api.cjs');
const {updateAccount}=require('./update-policy.cjs');
const delay = ms=>new Promise(resolve=>setTimeout(resolve,ms));
// Persist an in-flight marker before every mutation: a restart never blindly replays a POST.
async function runSerialTask(task, api, save, shouldStop = ()=>false, wait = delay) {
  let persistenceError;
  const originalSave=save;
  save=async()=>{try{return await originalSave();}catch(e){persistenceError=e;throw e;}};
  task.status = 'running'; task.error = ''; await save();
  try {
    let users = await api.users(task.tenantId);
    if (task.membershipTenantId) {
      const members = await api.request(`/api/platform/tenants/${task.membershipTenantId}/members`);
      if (!Array.isArray(members)) throw new ApiError('CONTRACT','成员接口不可用');
    }
    for (const entry of task.entries) {
      if (shouldStop()) {task.status='paused';break;}
      if (['done','updated','existing','failed','conflict'].includes(entry.status)) continue;
      try {
        if (entry.status === 'sending' || entry.status === 'unknown') {
          if(entry.operation==='update'){entry.status='unknown';throw new ApiError('UNRESOLVED','更新或密码重置结果未知，不能通过资料查询确认密码；请人工核对，不自动重发');}
          users = await api.users(task.tenantId);
          const found = findExisting(entry.person, users);
          if (!found) {entry.status='unknown';throw new ApiError('UNRESOLVED','无法确定之前的新增结果，请单独核对；不会自动重发');}
          entry.userId = String(found.id); entry.status='created';
        }
        if (!entry.userId) {
          if(task.passwordMode==='schoolIdentifier'){
            if(!/^[a-zA-Z][a-zA-Z0-9_-]{1,31}$/.test(task.schoolCode||'') || !entry.person.originalUid)throw new ApiError('VALIDATION','学校代号或学号缺失');
            entry.password ||= task.schoolCode+entry.person.originalUid;
          }
          if(task.updateExisting && !await updateAccount(entry,users,task,api,save))entry.operation='create';
        }
        if (!entry.userId) {
          const found = findExisting(entry.person, users);
          if (found) {entry.userId=String(found.id);entry.wasExisting=true;entry.status='created';}
          else {
            if(['phone','schoolPhone'].includes(task.passwordMode) && !/^\+?\d{7,15}$/.test(entry.person.phone || ''))throw new ApiError('VALIDATION','手机号初始密码要求有效手机号');
            if(task.passwordMode==='schoolPhone' && !/^[a-zA-Z][a-zA-Z0-9_-]{1,31}$/.test(task.schoolCode || ''))throw new ApiError('VALIDATION','学校代号无效，请重新创建导入任务');
            // Old tasks without a mode keep their original random-password behavior.
            entry.password ||= task.passwordMode==='schoolPhone' ? task.schoolCode + entry.person.phone : task.passwordMode==='phone' ? entry.person.phone : crypto.randomBytes(18).toString('base64url') + '!9aA';
            entry.status='sending'; await save();
            const p=entry.person;
            let id;
            try {
              id=await api.request('/api/v1/system/user/add',{uid:p.uid,userName:p.userName,nickName:p.nickName,phone:p.phone || undefined,email:p.email || undefined,password:entry.password,role:'User'});
              if (!/^[1-9]\d*$/.test(String(id)) || typeof id==='number' && !Number.isSafeInteger(id)) throw new ApiError('RESPONSE','新增接口未返回有效安全 ID');
            } catch(e) {
              // Even a 5xx/business error may follow a partially committed server operation.
              entry.status='unknown'; throw e;
            }
            entry.userId=String(id); entry.confirmedCreation=true; entry.status='created';
            users.push({...p,id,tenantId:task.tenantId}); await save();
          }
        }
        if (task.membershipTenantId) {
          entry.status='membership'; await save();
          await api.membership(task.membershipTenantId,entry.userId);
        }
        entry.status=entry.confirmedUpdate?'updated':entry.wasExisting?'existing':'done';entry.error='';await save();
      } catch(e) {
        if(persistenceError)throw persistenceError;
        entry.error=e.message;
        if (entry.status !== 'unknown' && entry.status !== 'membership') entry.status=e.code==='CONFLICT'?'conflict':'failed';
        await save();
        // Isolate uncertain writes too: retain their marker, but continue unrelated accounts.
        if (pauses(e) && !['NETWORK','RESPONSE'].includes(e.code)) throw e;
      }
      await wait(task.intervalMs);
    }
    if(task.status==='running') task.status=task.entries.some(e=>!['done','updated','existing'].includes(e.status))?'partial':'completed';
  } catch(e) {task.status='paused';task.error=e.message;}
  if(persistenceError)throw persistenceError;
  await save();
}
async function runTask(task, api, save, shouldStop = ()=>false, wait = delay) {
  const concurrency=Math.max(1,Math.min(5,Math.floor(Number(task.concurrency)||1)));
  // Membership and uncertain previous writes are reconciled serially before any new writes.
  if(concurrency===1 || task.membershipTenantId || task.entries.some(e=>['sending','unknown'].includes(e.status)))
    return runSerialTask(task,api,save,shouldStop,wait);
  task.status='running';task.error='';await save();
  let halted=false,fatal,saveChain=Promise.resolve(),gate=Promise.resolve(),cursor=0,first=true;
  const persist=()=>{
    saveChain=saveChain.then(save).catch(e=>{halted=true;fatal=e;throw e;});
    return saveChain;
  };
  const admit=()=>{
    const turn=gate.then(async()=>{
      if(!first)await wait(Math.max(250,Number(task.intervalMs)||250));
      first=false;return !halted && !shouldStop();
    });
    gate=turn.catch(()=>{});return turn;
  };
  try{
    const users=await api.users(task.tenantId);
    const pending=task.entries.filter(e=>!['done','updated','existing','failed','conflict'].includes(e.status));
    const seen=new Set();
    for(const e of pending){
      const keys=['uid','userName','phone','email'].filter(k=>e.person[k]).map(k=>k+':'+String(e.person[k]).toLowerCase());
      if(keys.some(k=>seen.has(k))){e.status='conflict';e.error='本批次身份字段重复，请在预览中去重后重新导入';}
      keys.forEach(k=>seen.add(k));
    }
    const worker=async()=>{
      while(!halted && !shouldStop()){
        const e=pending[cursor++];if(!e)return;
        if(e.status==='conflict')continue;
        if(!await admit())return;
        const child={...task,entries:[e],intervalMs:0};
        await runSerialTask(child,{...api,users:async()=>users,request:api.request.bind(api)},persist,()=>halted||shouldStop(),async()=>{});
        if(child.status==='paused'){halted=true;if(child.error)task.error=child.error;}
      }
    };
    const results=await Promise.allSettled(Array.from({length:concurrency},()=>worker()));
    const rejected=results.find(r=>r.status==='rejected');
    if(rejected)throw rejected.reason;
    task.status=halted||shouldStop()?'paused':task.entries.some(e=>!['done','updated','existing'].includes(e.status))?'partial':'completed';
  }catch(e){task.status='paused';task.error=e.message;}
  if(fatal)throw fatal;
  await save();
}
module.exports={runTask};
