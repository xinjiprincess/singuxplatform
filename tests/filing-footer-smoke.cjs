const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage();
  await page.route('**/*',route=>{
   const u=new URL(route.request().url());
   if(u.pathname.startsWith('/api/') || u.pathname.includes('/api/'))return route.fulfill({json:{code:'0000',success:true,data:u.pathname.includes('tenant/config')?{authType:1,siteName:'Singu X',loginPageText:'Singu X',loginPageSubText:'智能体开发平台'}:null}});
   if(!['127.0.0.1','localhost'].includes(u.hostname))return route.abort();
   return route.continue();
  });
  fs.mkdirSync('tmp/filing-screenshots',{recursive:true});
  for(const [name,width,height] of [['desktop',1440,900],['mobile',390,844]]){
   await page.setViewportSize({width,height});
   await page.goto('http://127.0.0.1:3000/login',{waitUntil:'domcontentloaded',timeout:180000});
   const footer=page.getByRole('contentinfo',{name:'网站备案信息'});
   await footer.waitFor({timeout:180000});
   assert.equal(await footer.getByRole('link',{name:'蜀ICP备2026030409号'}).getAttribute('href'),'https://beian.miit.gov.cn/');
   assert.equal(await footer.getByRole('link',{name:'公安备案查询'}).getAttribute('href'),'https://beian.mps.gov.cn/#/query/webSearch');
   const box=await footer.boundingBox();assert.ok(box&&box.y>=0&&box.y+box.height<=height+1);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`tmp/filing-screenshots/${name}.png`});
  }
  console.log('PASS: desktop/mobile login footer visible, correct links, no horizontal overflow. API calls mocked.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
