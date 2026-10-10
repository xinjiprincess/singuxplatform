const fields=['id','uid','username','email','phone'];
function queryParams(query){
  const params=new URLSearchParams();
  for(const field of fields){if(query[field]===undefined||query[field]==='')continue;const value=String(query[field]).trim();if(!value)continue;if(field==='id'&&(!/^[1-9]\d*$/.test(value)||(typeof query[field]==='number'&&!Number.isSafeInteger(query[field]))))throw new Error('用户 ID 无效');params.set(field,value);}
  if(!params.size)throw new Error('至少填写一个查询条件');return params.toString();
}
function safeUser(user,profile){
  if(!user||!user.id)throw new Error('详情响应为空');
  if(typeof user.id==='number'&&!Number.isSafeInteger(user.id))throw new Error('用户 ID 超出安全整数范围，需服务器返回字符串');
  if(profile.scope!=='single'&&String(user.tenantId)!==String(profile.tenantId))throw new Error('用户不属于目标租户');
  const {password,...rest}=user;return {...rest,id:String(user.id)};
}
async function matchRow(api,row,profile){
  const matches=[];
  for(const field of fields){if(!String(row[field]||'').trim())continue;try{matches.push(safeUser(await api.userDetail({[field]:row[field]}),profile));}catch(error){if(error.code==='4000')continue;throw error;}}
  if(!matches.length)throw new Error('未查到用户或查询条件被服务器拒绝');
  if(new Set(matches.map(u=>u.id)).size!==1)throw new Error('多个标识对应不同用户');
  const user=matches[0];
  for(const field of fields){const actual=field==='username'?user.userName:user[field];if(row[field]&&String(actual||'').trim().toLowerCase()!==String(row[field]).trim().toLowerCase())throw new Error(`身份冲突：${field} 与服务器不一致`);}
  if(row.name&&String(user.nickName||'').trim()!==row.name.trim())throw new Error('姓名与服务器不一致');
  return user;
}
async function runRoles(batch,api,profile,save,stopped,wait=ms=>new Promise(r=>setTimeout(r,ms))){
  for(const row of batch.rows){
    if(stopped())break;if(!['ready','unknown','sending'].includes(row.status))continue;
    try{
      const current=safeUser(await api.userDetail({id:row.userId}),profile);
      if(current.userName!==row.login)throw new Error('登录名已变化，请重新查询名单');
      if(current.role===row.targetRole){row.status='done';row.currentRole=current.role;row.error='';await save();continue;}
      if(['unknown','sending'].includes(row.status)){row.status='review';row.error='上次结果未知，当前角色未达到目标；请重新查询后再提交';await save();continue;}
      if(current.role!==row.currentRole)throw new Error('角色已被其他操作修改，请重新查询');
      row.status='sending';await save();
      await api.updateUser(row.userId,{role:row.targetRole});
      const after=safeUser(await api.userDetail({id:row.userId}),profile);
      if(after.role!==row.targetRole)throw new Error('更新响应成功，但回读角色不一致');
      row.status='done';row.currentRole=after.role;row.error='';
    }catch(error){const uncertain=row.status==='sending';row.status=uncertain?'unknown':'failed';row.error=error.message;await save();if(require('./api.cjs').pauses(error)){batch.status='paused';return;}}
    await save();await wait(500);
  }
  batch.status=stopped()?'paused':batch.rows.some(r=>['ready','unknown','sending'].includes(r.status))?'paused':'completed';await save();
}
module.exports={queryParams,safeUser,matchRow,runRoles};
