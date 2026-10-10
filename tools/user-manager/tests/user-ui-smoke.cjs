const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const path=require('node:path');const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--allow-file-access-from-files']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:850}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
 const data={profiles:[{id:'p',name:'测试环境'}],keys:[{id:'k',kind:'platform',enabled:true,profileId:'p',name:'测试 Key'}],sheets:[],issues:[],rows:[],tasks:[],active:null,roleBatch:{id:'b',baseUrl:'https://example.invalid',status:'prepared',rows:[{rowId:'0',name:'测试用户',userId:'1',login:'cdut001',currentRole:'User',targetRole:'Admin',status:'ready'}]}};
 window.manager=new Proxy({},{get:(_,name)=>async()=>name==='state'?data:name==='userDetail'?{id:'1',userName:'cdut001',nickName:'测试用户',role:'User',status:'Enabled'}:null});
 });
 await page.goto(require('node:url').pathToFileURL(path.resolve(__dirname,'../dist/index.html')).href);
 await page.getByRole('menuitem',{name:'用户查询 / 角色更新'}).click();
 await page.getByRole('combobox').first().click();await page.getByText('测试环境 · 测试 Key',{exact:true}).click();
 await page.getByRole('textbox',{name:'查询值'}).fill('cdut001');await page.getByRole('button',{name:/查询$/}).click();
 await page.getByRole('button',{name:'保存修改'}).waitFor();
 await page.getByRole('tab',{name:'批量角色更新'}).click();await page.getByRole('button',{name:'一键更新全部'}).waitFor();
 fs.mkdirSync(path.resolve(__dirname,'../artifacts'),{recursive:true});await page.screenshot({path:path.resolve(__dirname,'../artifacts/user-roles.png'),fullPage:true});
 assert.deepEqual(errors,[]);console.log('User query and role update UI smoke passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
