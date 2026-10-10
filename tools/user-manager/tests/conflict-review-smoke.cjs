const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http');
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const x=require('xlsx');
const root=path.resolve(__dirname,'..'),temp=fs.mkdtempSync(path.join(os.tmpdir(),'singux-review-test-'));
const fixture=path.join(temp,'users.xlsx'),book=x.utils.book_new();
x.utils.book_append_sheet(book,x.utils.aoa_to_sheet([['学号','姓名','手机号','邮箱'],['001','Test Student','13800138000','student@example.invalid']]),'Users');x.writeFile(book,fixture);
let user={id:'20',uid:'email-registration',userName:'old',nickName:'Old Nickname',phone:'',email:'student@example.invalid',role:'User',status:'Enabled'},posts=0,app;
const server=http.createServer(async(req,res)=>{
 let raw='';for await(const part of req)raw+=part;
 let data;
 if(req.url.endsWith('/list'))data={records:[user],total:1};
 else if(req.url.includes('/detail?'))data=user;
 else if(req.url.endsWith('/20/update')){const body=JSON.parse(raw);assert.equal(body.password,'cdut001');assert.equal(body.role,'User');assert.ok(!('uid' in body));user={...user,...body};delete user.password;posts++;data=null;}
 else {res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type','application/json');res.end(JSON.stringify({code:'0000',data}));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 app=await _electron.launch({executablePath:require('electron'),args:[root],env:{...process.env,NODE_ENV:'test',SINGUX_MANAGER_TEST_DATA:temp}});
 const page=await app.firstWindow();await page.getByRole('heading',{name:'导入用户',exact:true}).waitFor();
 await app.evaluate(({dialog},file)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]});dialog.showMessageBox=async()=>({response:1});},fixture);
 const invoke=(name,input)=>page.evaluate(({name,input})=>window.manager[name](input),{name,input});
 await invoke('saveProfile',{id:'local',name:'Mock review',baseUrl:`http://127.0.0.1:${server.address().port}`,scope:'single'});
 let state=await invoke('saveKey',{name:'Mock',kind:'platform',profileId:'local',secret:'fake-test-key'});
 const keyId=state.keys[0].id;
 await invoke('choose',{});state=await invoke('preview',{schoolCode:'cdut'});
 const options=state.previewOptions;
 const wait=async()=>{for(let i=0;i<100;i++){state=await invoke('state');if(!state.active)return;await new Promise(r=>setTimeout(r,100));}throw Error('Task timeout');};
 await invoke('startTask',{keyId,all:true,options});await wait();
 assert.equal(state.tasks[0].entries[0].status,'conflict');assert.equal(posts,0);
 await page.getByRole('menuitem',{name:'任务中心'}).click();
 await page.getByRole('combobox',{name:'选择冲突账号'}).click();await page.getByText('Test Student · cdut001',{exact:true}).click();
 await page.getByRole('button',{name:'查询并审核身份'}).click();
 const modal=page.getByRole('dialog',{name:'冲突身份审核'});await modal.waitFor();await page.waitForTimeout(500);
 await page.screenshot({path:path.join(root,'artifacts','conflict-review.png')});
 await modal.locator('textarea').fill('已核对报名记录及本人提供的账号信息');
 await modal.locator('input').first().fill('20');
 await modal.getByRole('checkbox').check();await modal.getByRole('button',{name:'保存身份审核'}).click();await modal.waitFor({state:'hidden'});
 assert.equal(posts,0);
 state=await invoke('state');const task=state.tasks[0];assert.ok(task.entries[0].manualBinding);
 await invoke('retryTask',{id:task.id,entryId:task.entries[0].person.id});await wait();assert.equal(posts,1);assert.equal(state.tasks[0].entries[0].status,'updated');assert.equal(user.uid,'email-registration');
 // Reimport exercises the stored binding rather than relying on the original task.
 await invoke('startTask',{keyId,all:true,options});await wait();assert.equal(state.tasks[0].entries[0].status,'updated');assert.equal(posts,2);
 const person=state.rows[0];await invoke('editRow',{...person,phone:''});
 const completed=await invoke('completeContacts',{keyId});assert.equal(completed.completion.completed,1);assert.equal(completed.rows[0].phone,'13800138000');assert.equal(posts,2);
 console.log('PASS: conflict review UI, no write on approval, bound update, reimport and read-only contact completion; production requests: 0');
})().then(()=>finish(0),e=>{console.error(e);finish(1);});
function finish(code){if(app)app.process().kill();server.closeAllConnections();server.close();setTimeout(()=>process.exit(code),500);}
