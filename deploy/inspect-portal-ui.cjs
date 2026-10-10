const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(process.env.PORTAL_URL || 'http://127.0.0.1:18093/zhichuangbei/login', { waitUntil: 'networkidle', timeout: 60000 });
    await page.screenshot({ path: path.join(process.env.TEMP, 'singux-portal-desktop.png'), fullPage: true });
    console.log(JSON.stringify({ url: page.url(), title: await page.title(), text: (await page.locator('body').innerText()).slice(0, 2500), inputs: await page.locator('input').evaluateAll(items => items.map(e => ({type:e.type, placeholder:e.placeholder, id:e.id}))), errors }, null, 2));
    console.log('Login accent:', await page.getByRole('button',{name:/^登\s*录$/}).evaluate(e=>getComputedStyle(e).backgroundColor));
    if (process.env.PORTAL_TEST_PASSWORD) {
      await page.locator('#login_phoneOrEmail').fill('admin');
      await page.locator('#login_password').fill(process.env.PORTAL_TEST_PASSWORD);
      await page.getByRole('button', { name: /^登\s*录$/ }).click();
      await page.waitForURL('**/zhichuangbei/home**', {timeout:60000});
      await page.waitForLoadState('networkidle', {timeout:60000});
      await page.waitForFunction(() => document.body.innerText.trim().length > 20, {timeout:60000});
      await page.screenshot({path:path.join(process.env.TEMP,'singux-portal-home.png'),fullPage:true});
      console.log(JSON.stringify({authenticatedUrl:page.url(),text:(await page.locator('body').innerText()).slice(0,1800),errors},null,2));
      const admin = await browser.newContext({viewport:{width:1440,height:1000}});
      const auth = await admin.request.post('http://127.0.0.1:18093/api/user/passwordLogin',{data:{phoneOrEmail:'admin',password:process.env.PORTAL_TEST_PASSWORD}});
      if ((await auth.json()).code !== '0000') throw new Error('Root login failed');
      const selected = await admin.request.post('http://127.0.0.1:18093/api/session/tenant/select',{headers:{Origin:'http://127.0.0.1:18093'},data:{tenantId:1}});
      const selection = await selected.json();
      if (selection.code !== '0000') throw new Error('Root selection failed: '+selection.code);
      await admin.addInitScript(token => localStorage.setItem('ACCESS_TOKEN',token),selection.data.token);
      const management = await admin.newPage();
      await management.goto('http://127.0.0.1:18093/platform/portals',{waitUntil:'networkidle',timeout:60000});
      await management.getByRole('heading',{name:'专用平台',exact:true}).waitFor();
      await management.getByRole('link',{name:'/zhichuangbei',exact:true}).waitFor();
      await management.getByRole('row').filter({has:management.getByRole('link',{name:'/zhichuangbei',exact:true})}).getByRole('button').filter({hasText:/编\s*辑/}).click();
      await management.getByText('编辑专用平台',{exact:true}).waitFor();
      await management.screenshot({path:path.join(process.env.TEMP,'singux-portal-management.png'),fullPage:true});
      console.log('Management list and edit dialog rendered');
      await admin.close();
    }
    const mobile = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1'});
    await mobile.goto('http://127.0.0.1:18093/zhichuangbei/login',{waitUntil:'networkidle',timeout:60000});
    await mobile.screenshot({path:path.join(process.env.TEMP,'singux-portal-mobile.png'),fullPage:true});
    console.log(JSON.stringify({mobileUrl:mobile.url(),mobileText:(await mobile.locator('body').innerText()).slice(0,700)},null,2));
    const fits = await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
    if (!fits) throw new Error('Mobile login has horizontal overflow');
    if (errors.length) throw new Error('Portal runtime errors: '+errors.join('; '));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
