const {test}=require('node:test'),assert=require('node:assert/strict');
const {completeContacts}=require('../desktop/contact-completion.cjs');
const options={schoolCode:'cdut',passwordMode:'schoolIdentifier',requireBoth:false};
const row={id:'row',uid:'cdut:person:001',originalUid:'001',userName:'cdut001',nickName:'Demo',phone:'',email:'',sources:[],errors:[]};
const user={...row,id:'10',phone:'13800138000',email:'demo@example.invalid',role:'User',status:'Enabled'};
test('fills missing real contacts for strongly matched user without changing source',()=>{
 const result=completeContacts([row],[user],options);
 assert.equal(result.completed,1);assert.equal(result.rows[0].phone,user.phone);assert.equal(result.rows[0].email,user.email);assert.deepEqual(result.rows[0].errors,[]);assert.equal(row.phone,'');
});
test('one contact suffices by default, existing contact not overwritten',()=>{
 const result=completeContacts([{...row,phone:'13900139000'}],[user],options);
 assert.equal(result.rows[0].phone,'13900139000');assert.equal(result.rows[0].email,user.email);
 assert.deepEqual(completeContacts([{...row,email:user.email}],[],options).rows[0].errors,[]);
});
test('no fabricated contact, ambiguous and protected targets do not fill',()=>{
 for(const users of [[],[user,{...user,id:'11'}],[{...user,role:'Admin'}],[{...user,status:'Disabled'}],[{...user,uid:'001'}]]){
  const result=completeContacts([row],users,options);assert.equal(result.completed,0);assert.equal(result.rows[0].phone,'');assert.ok(result.rows[0].errors.length);
 }
});
test('strict both-contact validation is still opt-in; invalid server fields stay empty',()=>{
 assert.ok(completeContacts([{...row,email:user.email}],[],{...options,requireBoth:true}).rows[0].errors.length);
 const result=completeContacts([row],[{...user,phone:'bad',email:'bad'}],options);assert.equal(result.completed,0);
});
