const {ApiError}=require('./api.cjs');
const norm=v=>String(v??'').trim();
const email=v=>norm(v).toLowerCase();
function snapshot(u){return Object.fromEntries(['id','uid','userName','nickName','phone','email','role','status'].map(k=>[k,norm(u[k])]));}
function candidates(row,users){
  const raw=norm(row.originalUid);
  return users.filter(u=>(row.uid&&norm(u.uid)===row.uid)||(raw&&norm(u.uid)===raw)||(row.phone&&norm(u.phone)===row.phone)||(row.email&&email(u.email)===email(row.email))||(row.userName&&norm(u.userName)===row.userName));
}
function personIdentity(row){return JSON.stringify(['uid','originalUid','userName','nickName','phone','email'].map(k=>norm(row[k])));}
function resolveUpdate(row,users,binding){
  const raw=norm(row.originalUid);
  const hits=candidates(row,users);
  if(!hits.length){if(binding)throw new ApiError('CONFLICT','审核绑定的账号已无法匹配，请重新审核');return null;}
  if(new Set(hits.map(u=>norm(u.id))).size!==1)throw new ApiError('CONFLICT','学号或联系方式对应多个用户，不能自动更新');
  const u=hits[0];
  if(u.role!=='User' || u.status!=='Enabled')throw new ApiError('CONFLICT','仅允许更新启用的普通 User 账号；管理员、停用或角色未知账号需单独处理');
  if(binding){
    const expected={...binding.target,userName:row.userName,nickName:row.nickName,phone:row.phone||binding.target.phone,email:row.email||binding.target.email};
    if(binding.person!==personIdentity(row) || norm(binding.target.id)!==norm(u.id) || (!sameSnapshot(u,binding.target)&&!sameSnapshot(u,expected)))throw new ApiError('CONFLICT','审核绑定的人员或服务器资料已变化，请重新审核');
    return u;
  }
  const scoped=row.uid && norm(u.uid)===row.uid;
  const legacy=raw && norm(u.uid)===raw && norm(u.nickName)===norm(row.nickName) && ((row.email&&email(u.email)===email(row.email))||(row.phone&&norm(u.phone)===row.phone));
  // Updates preserve uid, including IDs originally assigned during email registration.
  const migrated=raw && norm(row.userName)!=='' && norm(u.userName)===norm(row.userName) && norm(u.nickName)===norm(row.nickName) && ((row.email&&email(u.email)===email(row.email))||(row.phone&&norm(u.phone)===row.phone));
  if(!scoped&&!legacy&&!migrated)throw new ApiError('CONFLICT','未能确认同一人：旧学号或目标登录名必须同时匹配姓名及至少一项联系方式；仅邮箱相同需人工核实，不能自动覆盖');
  return u;
}
function sameSnapshot(a,b){return JSON.stringify(snapshot(a))===JSON.stringify(snapshot(b));}
async function updateAccount(entry,users,task,api,save){
  const found=resolveUpdate(entry.person,users,entry.manualBinding);
  if(!found){if(entry.approvedTarget)throw new ApiError('CONFLICT','预览中的目标用户已不存在，停止该账号更新');return false;}
  if(!entry.approvedTarget || !sameSnapshot(found,entry.approvedTarget))throw new ApiError('CONFLICT','已有账号与提交确认时不同，请重新生成任务确认');
  const id=norm(found.id);
  if(!/^[1-9]\d*$/.test(id))throw new ApiError('CONTRACT','更新目标 ID 无效');
  const current=await api.request(`/api/v1/system/user/detail?id=${encodeURIComponent(id)}`);
  if(!current || !sameSnapshot(current,entry.approvedTarget))throw new ApiError('CONFLICT','提交前目标账号发生变化，请重新确认');
  const p=entry.person;
  const body={userName:p.userName,nickName:p.nickName,phone:p.phone||current.phone||undefined,email:p.email||current.email||undefined,password:entry.password,role:'User'};
  // The update API cannot modify uid. Keep the legacy uid and never infer a password from readback.
  entry.operation='update';entry.userId=id;entry.status='sending';await save();
  try{
    await api.request(`/api/v1/system/user/${id}/update`,body);
    const result=await api.request(`/api/v1/system/user/detail?id=${encodeURIComponent(id)}`);
    if(!result || norm(result.id)!==id || result.role!=='User' || result.status!=='Enabled' || norm(result.uid)!==norm(current.uid) || ['userName','nickName','phone','email'].some(k=>body[k]!==undefined && norm(result[k])!==body[k]))throw new ApiError('RESPONSE','更新响应成功但资料回读不一致，需单独核对');
  }catch(e){entry.status='unknown';throw e;}
  entry.confirmedUpdate=true;entry.status='created';
  Object.assign(found,body);delete found.password;
  await save();return true;
}
module.exports={resolveUpdate,snapshot,updateAccount,candidates,personIdentity};
