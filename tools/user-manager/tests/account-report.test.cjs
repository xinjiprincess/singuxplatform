const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const XLSX=require('xlsx');
const {accountRows,writeAccountWorkbook}=require('../desktop/account-report.cjs');
test('account report reveals only confirmed creations and preserves literal strings',()=>{
 const person={id:'1',nickName:'=SUM(1,2)',userName:'0000123',sources:[]};
 const task={entries:[{person,status:'done',confirmedCreation:true,password:'013800138000'},{person,status:'existing',password:'must-not-export',wasExisting:true},{person,status:'unknown',password:'must-not-export'}]};
 assert.equal(accountRows(task)[0].password,'••••••••');
 assert.deepEqual(accountRows(task,true).map(r=>r.password),['013800138000','','']);
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'account-report-'));
 try{const file=path.join(dir,'accounts.xlsx');writeAccountWorkbook(task,file);const sheet=XLSX.readFile(file).Sheets['导入账号密码'];assert.equal(sheet.B2.v,'0000123');assert.equal(sheet.C2.v,'013800138000');assert.equal(sheet.A2.t,'s');assert.equal(sheet.A2.f,undefined);assert.equal(sheet.C3.v,'');}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
