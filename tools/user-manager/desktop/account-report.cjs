const XLSX=require('xlsx');
const names={pending:'待导入',sending:'结果待核对',unknown:'结果待核对',done:'新增完成',updated:'更新完成',existing:'已存在，未改密码',failed:'失败',conflict:'身份冲突',created:'账号已创建',membership:'成员关系待完成'};
function accountRows(task,reveal=false){
  return task.entries.map(e=>({id:e.person.id,name:e.person.nickName,account:e.person.userName,
    password:(e.confirmedCreation || e.confirmedUpdate) && e.password ? (reveal?e.password:'••••••••') : '',
    passwordNote:(e.confirmedCreation || e.confirmedUpdate) && e.password?'本次创建或重置的初始密码':e.wasExisting||e.status==='existing'?'已有账号，密码未知且未修改':'未确认创建，不提供密码',
    status:names[e.status]||e.status,userId:e.userId||'',sources:(e.person.sources||[]).map(s=>`${s.file} / ${s.sheet} / ${s.row}`).join('; ')}));
}
function writeAccountWorkbook(task,file){
  const rows=accountRows(task,true);
  const data=[['姓名','登录账号','初始密码','密码说明','导入结果','用户ID','来源'],...rows.map(r=>[r.name,r.account,r.password,r.passwordNote,r.status,r.userId,r.sources])];
  const sheet=XLSX.utils.aoa_to_sheet(data);
  sheet['!cols']=[{wch:16},{wch:24},{wch:28},{wch:38},{wch:24},{wch:22},{wch:60}];
  const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,sheet,'导入账号密码');
  XLSX.writeFile(book,file);
}
function writeUnsuccessfulWorkbook(task,file){
  const entries=task.entries.filter(e=>!['done','updated','existing'].includes(e.status));
  const data=[['姓名','登录账号','学号/工号','学校代号','手机号','邮箱','处理状态','错误原因','用户ID','处理建议','来源'],...entries.map(e=>[
    e.person.nickName,e.person.userName,e.person.originalUid||'',task.schoolCode||'',e.person.phone||'',e.person.email||'',names[e.status]||e.status,e.error||'',e.userId||'',
    ['unknown','sending'].includes(e.status)?'可能已创建或更新，请先在平台核对，不要直接重新导入':e.status==='membership'?'账号已创建，仅处理成员关系':e.status==='pending'?'尚未提交':e.status==='created'?'账号已创建，后续步骤未完成':'核对错误字段后单独处理，不覆盖已有账号',
    (e.person.sources||[]).map(s=>`${s.file} / ${s.sheet} / ${s.row}`).join('; ')
  ])];
  const sheet=XLSX.utils.aoa_to_sheet(data);sheet['!cols']=[16,24,24,16,20,32,22,65,22,65,60].map(wch=>({wch}));
  const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,sheet,'未成功账号');XLSX.writeFile(book,file);
}
module.exports={accountRows,writeAccountWorkbook,writeUnsuccessfulWorkbook};
