const {test}=require('node:test');
const assert=require('node:assert/strict');
const c=require('../desktop/core.cjs');
const options={schoolCode:'test',usernamePrefix:'stu_',requireBoth:true};
test('school prefix preserves identifier zeros and requires identifier and phone',()=>{
 const options={schoolCode:'cdut',usernameMode:'schoolIdentifier',passwordMode:'schoolPhone'};
 const row={id:'1',uid:'000123',nickName:'Test',phone:'13800138000',sources:[]};
 assert.equal(c.normalize([row],options)[0].userName,'cdut000123');
 assert.ok(c.normalize([{...row,uid:''}],options)[0].errors.length);
 assert.ok(c.normalize([{...row,phone:''}],options)[0].errors.length);
});
function person(overrides={}) {return c.normalize([{id:'one',uid:'0012',nickName:'Test User',phone:'13800138000',email:'test@example.invalid',sources:[],...overrides}],options)[0];}
test('header mapping and leading-zero identifiers',()=>{
  const rows=[['Export'],['学号','姓名','手机号','邮箱'],['0012','Test User','13800138000','test@example.invalid']];
  const sheet={id:'sheet',file:'test.xls',name:'Users',rows,...c.autoMapping(rows)};
  const parsed=c.normalize(c.extract(sheet,options),options);
  assert.equal(parsed[0].uid,'test:person:0012');assert.equal(parsed[0].userName,'stu_0012');assert.deepEqual(parsed[0].errors,[]);
});
test('known registration template separates main people, members and teachers',()=>{
  const rows=Array.from({length:6},()=>Array(42).fill(''));
  Object.assign(rows[2],{6:'工号/学号',7:'姓名',15:'团队成员情况'});
  Object.assign(rows[3],{0:'1',4:'Test team',6:'001',7:'Leader',9:'13800138000',11:'leader@example.invalid'});
  Object.assign(rows[4],{15:'002',16:'Member',20:'13800138001',22:'Teacher',24:'003',27:'13800138002'});
  const sheet={id:'test',file:'template.xls',name:'test',rows};
  assert.equal(c.extract(sheet,options).length,2);
  assert.equal(c.extract(sheet,{...options,includeTeachers:true}).length,3);
  assert.equal(c.extract(sheet,options)[1].sources[0].row,5);
});
test('deduplication merges only identical rows and retains conflicting values',()=>{
  const a=person();const b=person({id:'two'});
  assert.equal(c.deduplicate([a,b]).length,1);
  b.email='second@example.invalid';const conflict=c.deduplicate([a,b]);
  assert.equal(conflict.length,2);assert.ok(conflict.every(r=>r.errors.length));
  assert.equal(conflict[1].email,'second@example.invalid');
});
test('contact conflicts, scientific IDs, invalid usernames and missing contacts block',()=>{
  assert.ok(c.deduplicate([person(),person({id:'two',uid:'0022'})]).every(r=>r.errors.length));
  assert.ok(person({uid:'1.23E+12'}).errors.length);
  assert.ok(person({userName:'bad name'}).errors.length);
  assert.ok(person({phone:'',email:''}).errors.length);
});
test('default identifier rule preserves zeros and does not invent missing student IDs',()=>{
  const opt={...options,usernameMode:'identifier',passwordMode:'phone'};
  const records=[{id:'1',uid:'000012',userName:'ignored',nickName:'Example',phone:'13800138000',email:'test@example.invalid',sources:[]}];
  const r=c.normalize(records,opt)[0];assert.equal(r.userName,'000012');assert.deepEqual(r.errors,[]);
  assert.ok(c.normalize([{...records[0],uid:''}],opt)[0].errors.length);
  assert.ok(c.normalize([{...records[0],phone:''}],{...opt,requireBoth:false})[0].errors.length);
});
test('URL and AI mapping validation rejects unsafe values',()=>{
  for(const url of ['file:///tmp','https://name:password@example.invalid','https://example.invalid?key=secret','http://example.invalid'])assert.throws(()=>c.endpoint(url));
  assert.equal(c.endpoint('http://127.0.0.1:1234/'),'http://127.0.0.1:1234');
  assert.throws(()=>c.verifyMapping({role:0},4));assert.throws(()=>c.verifyMapping({uid:8},4));
  assert.throws(()=>c.verifyMapping({uid:1,phone:1},4));assert.throws(()=>c.verifyMapping(undefined,4));
  assert.deepEqual(c.verifyMapping({uid:0,nickName:1},2),{uid:0,nickName:1});
});
test('CSV formula neutralization and log redaction',()=>{
  assert.equal(c.csvCell('=SUM(A1)'), '"\'=SUM(A1)"');
  assert.ok(!c.redact('Bearer fake-secret sk-test test@example.com 13800138000').includes('fake-secret'));
});
