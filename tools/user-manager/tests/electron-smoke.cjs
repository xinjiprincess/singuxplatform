// Isolated desktop test. Every network endpoint and every person below is synthetic.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const {once}=require('node:events');
const {_electron}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const XLSX=require('xlsx');
const root=path.resolve(__dirname,'..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'singux-manager-test-'));
fs.mkdirSync(path.join(root,'artifacts'),{recursive:true});
const fixture=path.join(temp,'synthetic-users.xlsx');
const book=XLSX.utils.book_new();
XLSX.utils.book_append_sheet(book,XLSX.utils.aoa_to_sheet([['学号','姓名','手机号','邮箱'],['00001','Demo Person','13800138000','demo@example.invalid']]),'Users');
XLSX.writeFile(book,fixture);
const users=[{id:'1',uid:'seed',userName:'seed',phone:'',email:''}];
const seen=[];
const server=http.createServer(async(req,res)=>{
  let input='';for await(const chunk of req)input+=chunk;
  seen.push({url:req.url,key:req.headers.authorization});
  let data;
  if(req.url==='/api/v1/system/user/list')data={records:users,total:users.length};
  else if(req.url==='/api/v1/system/user/add'){
    const body=JSON.parse(input);assert.equal(body.role,'User');assert.equal(body.userName,'test00001');assert.equal(body.password,'test00001');
    users.push({...body,id:'2',status:'Enabled'});data='2';
  } else if(req.url==='/api/v1/system/user/detail?id=2'){
    data={...users.find(u=>u.id==='2')};delete data.password;
  } else if(req.url==='/api/v1/system/user/2/update'){
    const body=JSON.parse(input);assert.equal(body.password,'test00001');assert.equal(body.role,'User');assert.ok(!Object.hasOwn(body,'uid'));
    Object.assign(users.find(u=>u.id==='2'),body);data=null;
  } else if(req.url==='/v1/chat/completions') {
    assert.equal(req.headers.authorization,'Bearer not-a-real-model-key');
    assert.ok(!input.includes('demo@example.invalid'));assert.ok(!input.includes('13800138000'));
    const body=JSON.parse(input);assert.deepEqual(JSON.parse(body.messages[1].content),{headers:['学号','姓名','手机号','邮箱']});
    res.setHeader('content-type','application/json');res.end(JSON.stringify({choices:[{message:{content:JSON.stringify({mapping:{uid:0,nickName:1,phone:2,email:3}})}}]}));return;
  } else {res.writeHead(404);res.end();return;}
  res.setHeader('content-type','application/json');res.end(JSON.stringify({code:'0000',data}));
});
let app;
(async()=>{
  server.listen(0,'127.0.0.1');await once(server,'listening');
  const baseUrl=`http://127.0.0.1:${server.address().port}`;
  app=await _electron.launch({executablePath:require('electron'),args:[root],env:{...process.env,NODE_ENV:'test',SINGUX_MANAGER_TEST_DATA:temp}});
  const page=await app.firstWindow();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.getByRole('heading',{name:'导入用户',exact:true}).waitFor();
  await app.evaluate(({dialog},file)=>{
    dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]});
    dialog.showMessageBox=async()=>({response:1,checkboxChecked:false});
  },fixture);
  const invoke=(name,input)=>page.evaluate(({name,input})=>window.manager[name](input),{name,input});
  await invoke('saveProfile',{id:'local',name:'Local synthetic test',baseUrl,scope:'single'});
  for(const [id,name] of [['a','Import A'],['b','Import B']])await invoke('saveKey',{name,kind:'platform',profileId:'local',secret:`not-a-real-key-${id}`,enabled:true});
  await invoke('saveKey',{name:'Model test',kind:'model',baseUrl:baseUrl+'/v1',model:'deepseek-chat',secret:'not-a-real-model-key'});
  let state=await invoke('state');assert.equal(state.keys.length,3);assert.ok(!JSON.stringify(state).includes('not-a-real-key'));
  const encrypted=fs.readFileSync(path.join(temp,'manager.enc'));
  assert.ok(!encrypted.includes('not-a-real-key-a'));assert.ok(!encrypted.includes('not-a-real-model-key'));
  const keyId=state.keys.find(k=>k.name==='Import A').id;
  await invoke('testKey',keyId);assert.equal(seen.length,1);
  await page.getByRole('menuitem',{name:'API Key 管理'}).click();
  await page.getByRole('button',{name:/添加 API Key$/}).click();
  await page.getByLabel('名称',{exact:true}).fill('UI model key');
  await page.getByLabel('用途',{exact:true}).press('ArrowDown');
  await page.getByText('DeepSeek / 兼容模型 API Key',{exact:true}).click();
  await page.getByLabel('API Key',{exact:true}).fill('ui-fake-key');
  await page.getByRole('button',{name:/^确\s*定$/}).click();
  await page.getByRole('cell',{name:'UI model key',exact:true}).waitFor();
  state=await invoke('state');assert.equal(state.keys.length,4);
  await page.getByRole('menuitem',{name:'批量导入'}).click();
  await page.getByRole('button',{name:/添加表格$/}).click();
  await page.getByRole('cell',{name:'synthetic-users.xlsx',exact:true}).waitFor();
  await page.getByPlaceholder('例如 cdut').fill('test');
  await page.getByRole('button',{name:/生成 \/ 重新校验预览$/}).click();
  await page.getByRole('cell',{name:'Demo Person',exact:true}).waitFor();
  state=await invoke('state');assert.equal(state.rows.length,1);assert.deepEqual(state.rows[0].errors,[]);
  const suggestion=await invoke('suggest',{sheetId:state.sheets[0].id,keyId:state.keys.find(k=>k.name==='Model test').id});
  assert.deepEqual(suggestion.mapping,{uid:0,nickName:1,phone:2,email:3});
  await page.screenshot({path:path.join(root,'artifacts','desktop-preview.png'),fullPage:true});
  await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(900,650));
  await page.screenshot({path:path.join(root,'artifacts','desktop-compact.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
  await invoke('startTask',{keyId,all:true,ids:[],options:state.previewOptions,intervalMs:1000});
  for(let i=0;i<50;i++){state=await invoke('state');if(!state.active)break;await new Promise(r=>setTimeout(r,150));}
  assert.equal(state.tasks[0].status,'completed');assert.equal(seen.filter(r=>r.url.endsWith('/add')).length,1);
  assert.ok(seen.filter(r=>r.url.startsWith('/api/')).every(r=>r.key==='Bearer not-a-real-key-a'));
  assert.ok(!Object.hasOwn(state.tasks[0].entries[0],'password'));
  assert.equal(state.tasks[0].passwordMode,'schoolIdentifier');
  Object.assign(users.find(u=>u.id==='2'),{uid:'00001',userName:'user00001',phone:''});
  await invoke('startTask',{keyId,all:true,options:state.previewOptions,intervalMs:500});
  for(let i=0;i<50;i++){state=await invoke('state');if(!state.active)break;await new Promise(r=>setTimeout(r,150));}
  assert.equal(state.tasks[0].entries[0].status,'updated');
  assert.equal(seen.filter(r=>r.url.endsWith('/2/update')).length,1);
  const report=await invoke('accountReport',{id:state.tasks[0].id,reveal:true});assert.equal(report.rows[0].password,'test00001');
  assert.ok(!seen.some(r=>r.url.includes('/tenants/')));
  console.log('Mock create, legacy account update and reset-password report verified.');
  const closed=app.waitForEvent('close');app.process().kill();await closed;app=null;
  app=await _electron.launch({executablePath:require('electron'),args:[root],env:{...process.env,NODE_ENV:'test',SINGUX_MANAGER_TEST_DATA:temp}});
  const restoredPage=await app.firstWindow();await restoredPage.getByRole('heading',{name:'导入用户',exact:true}).waitFor();
  const restored=await restoredPage.evaluate(()=>window.manager.state());
  assert.equal(restored.keys.length,4);assert.equal(restored.tasks[0].status,'completed');assert.equal(restored.active,null);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['native UI','4 keys','OS-encrypted persistence','offline spreadsheet preview','compact layout','mock API import','fixed-key routing','AI header-only mapping','restart restore'],productionRequests:0,testData:temp}));
})().catch(async e=>{
  console.error(e);process.exitCode=1;
  if(app){const p=app.windows()[0];if(p){await p.screenshot({path:path.join(root,'artifacts','smoke-failure.png')}).catch(()=>{});console.error((await p.locator('body').innerText()).slice(0,5000));}}
}).finally(async()=>{if(app){app.process().kill();}server.closeAllConnections();server.close();});
