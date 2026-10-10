const {resolveUpdate}=require('./update-policy.cjs');
const {validate,deduplicate}=require('./core.cjs');

function completeContacts(rows,users,options){
  let completed=0,review=0;
  const result=rows.map(source=>{
    const row=structuredClone(source);
    if(!row.phone || !row.email){
      try{
        // Establish identity before filling: copied contacts must not become matching evidence.
        const user=resolveUpdate(row,users);
        if(user){
          const fields=[];
          const phone=String(user.phone||'').trim(),email=String(user.email||'').trim().toLowerCase();
          if(!row.phone && /^\+?\d{7,15}$/.test(phone)){row.phone=phone;fields.push('phone');}
          if(!row.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){row.email=email;fields.push('email');}
          if(fields.length){row.contactCompletion={userId:String(user.id),fields};completed++;}
        }
      }catch(e){if(e.code!=='CONFLICT')throw e;review++;}
    }
    row.errors=validate(row,options);
    return row;
  });
  return {rows:deduplicate(result),completed,review};
}
module.exports={completeContacts};
