const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');
const base = 'http://127.0.0.1:18093';

(async () => {
  if (!process.env.PORTAL_TEST_PASSWORD) throw new Error('PORTAL_TEST_PASSWORD required');
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  let previousWebsite, previousPortal, changedWebsite, changedPortal;
  const check = (value, message) => { if (!value) throw new Error(message); };
  const api = async (url, data) => {
    const response = data === undefined ? await context.request.get(base + url) : await context.request.put(base + url, { data, headers: { Origin: base } });
    const result = await response.json();
    check(result.code === '0000', `${url}: ${result.code}`);
    return result.data;
  };
  try {
    await context.request.post(base + '/api/user/passwordLogin', { data: { phoneOrEmail: 'admin', password: process.env.PORTAL_TEST_PASSWORD } });
    const selection = await context.request.post(base + '/api/session/tenant/select', { headers: { Origin: base }, data: { tenantId: 1 } });
    const result = await selection.json();
    check(result.code === '0000', 'Root selection failed');
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${result.data.token}` });
    await context.addInitScript(token => localStorage.setItem('ACCESS_TOKEN', token), result.data.token);
    previousWebsite = await api('/api/public/portals/website-backgrounds');
    previousPortal = (await api('/api/platform/portals')).find(p => p.slug === 'zhichuangbei');
    check(previousPortal, 'Competition missing');
    changedWebsite = await api('/api/platform/website-backgrounds', { backgrounds: { loginBackground: '/logo/logo-light.png', workspaceBackground: '/logo/logo-dark.png' }, previous: previousWebsite, reason: 'Local background regression' });
    changedPortal = await api('/api/platform/portals', { portal: { ...previousPortal, loginBackground: '/logo/logo-dark.png', workspaceBackground: '/logo/logo-light.png' }, previous: previousPortal, reason: 'Local background regression' });
    check((await api('/api/public/portals/website-backgrounds')).loginBackground === changedWebsite.loginBackground, 'Website save failed');
    check((await api('/api/public/portals/zhichuangbei')).loginBackground === changedPortal.loginBackground, 'Portal save failed');
    const stale = await context.request.put(base + '/api/platform/website-backgrounds', { headers: { Origin: base }, data: { backgrounds: previousWebsite, previous: previousWebsite, reason: 'Stale rejection test' } });
    check((await stale.json()).code === 'PORTAL_CONFLICT', 'Stale write accepted');
    const unsafe = await context.request.put(base + '/api/platform/website-backgrounds', { headers: { Origin: base }, data: { backgrounds: { loginBackground: 'https://external.invalid/a.png' }, previous: changedWebsite, reason: 'Unsafe rejection test' } });
    check((await unsafe.json()).code !== '0000', 'Unsafe path accepted');
    const anonymous = await browser.newContext();
    const denied = await anonymous.request.put(base + '/api/platform/website-backgrounds', { headers: { Origin: base }, data: { backgrounds: {}, previous: changedWebsite, reason: 'Unauthorized test' } });
    check((await denied.json()).code !== '0000', 'Anonymous write accepted');
    for (const [route, image] of [['/login', 'logo-light.png'], ['/zhichuangbei/login', 'logo-dark.png']]) {
      const page = await anonymous.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base + route, { waitUntil: 'networkidle' });
      check(await page.evaluate(name => [...document.querySelectorAll('div')].some(e => getComputedStyle(e).backgroundImage.includes(name)), image), 'Missing login background: ' + route);
      check(await page.locator('input[type="password"]').isVisible(), 'Missing login form');
      check(errors.length === 0, 'Login runtime error');
      await page.close();
    }
    await anonymous.close();
    const page = await context.newPage();
    await page.goto(base + '/platform/portals', { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: /官网背景/ }).click();
    await page.getByRole('dialog').waitFor();
    check(await page.getByRole('dialog').getByLabel('登录页背景图路径').inputValue() === changedWebsite.loginBackground, 'Management form not populated');
    check(await page.evaluate(() => [...document.querySelectorAll('div')].some(e => getComputedStyle(e, '::before').backgroundImage.includes('logo-dark.png'))), 'Missing workspace background');
    await page.screenshot({ path: path.join(process.env.TEMP, 'singux-background-management.png'), fullPage: true });
    console.log('PASS: website/portal persisted independently; stale/unsafe/anonymous writes rejected; login backgrounds and workspace CSS rendered; management dialog populated');
  } finally {
    try {
      if (changedPortal) await api('/api/platform/portals', { portal: previousPortal, previous: changedPortal, reason: 'Restore after local regression' });
      if (changedWebsite) await api('/api/platform/website-backgrounds', { backgrounds: previousWebsite, previous: changedWebsite, reason: 'Restore after local regression' });
    } finally { await browser.close(); }
  }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
