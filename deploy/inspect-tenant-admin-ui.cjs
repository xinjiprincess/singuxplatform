const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const base = process.env.TENANT_TEST_URL || 'http://127.0.0.1:18093';
  if (!['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw new Error('Local verification only');
  if (!process.env.PORTAL_TEST_PASSWORD) throw new Error('Local test password required');
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true });
  const output = path.resolve(__dirname, '../outputs/tenant-admin-ui-20261008');
  fs.mkdirSync(output, { recursive: true });
  try {
    for (const [name, viewport] of [['desktop', { width: 1440, height: 1000 }], ['mobile', { width: 390, height: 844 }]]) {
      const context = await browser.newContext({ viewport, locale: 'zh-CN' });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.goto(`${base}/login`, { waitUntil: 'networkidle', timeout: 60000 });
      await page.locator('#login_phoneOrEmail').fill('admin');
      await page.locator('#login_password').fill(process.env.PORTAL_TEST_PASSWORD);
      await page.getByRole('button', { name: /^登\s*录$|^Login$/i }).click();
      await page.getByPlaceholder(/搜索企业|Search enterprise/).waitFor({ timeout: 60000 });
      await page.screenshot({ path: path.join(output, `${name}-selection.png`), fullPage: true });
      const search = page.getByPlaceholder(/搜索企业|Search enterprise/);
      await search.fill('nonexistent-enterprise-acceptance');
      await page.getByText(/没有匹配的企业|No matching enterprises/).waitFor();
      await search.fill('');
      await page.getByRole('radio').first().check();
      await page.getByRole('button', { name: /进入企业|Enter enterprise|^进入$|^Enter$/i }).click();
      await page.waitForURL(/\/home/, { timeout: 60000 });
      await page.goto(`${base}/platform/tenants`, { waitUntil: 'networkidle', timeout: 60000 });
      await page.getByRole('button', { name: /新增企业|Create enterprise/ }).click();
      await page.getByLabel(/所有者用户 ID|Owner user ID/).waitFor();
      await page.screenshot({ path: path.join(output, `${name}-create.png`), fullPage: true });
      await page.keyboard.press('Escape');
      await page.goto(`${base}/system/user/manage`, { waitUntil: 'networkidle', timeout: 60000 });
      await page.getByRole('button', { name: /批量添加用户|Add users in bulk/ }).click();
      await page.getByRole('button', { name: /导入全部|Import all/ }).waitFor();
      await page.screenshot({ path: path.join(output, `${name}-batch.png`), fullPage: true });
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
      if (!fits) throw new Error(`${name}: horizontal page overflow`);
      if (errors.length) throw new Error(`${name}: ${errors.join('; ')}`);
      console.log(`PASS: ${name} selection, search, enterprise form, batch form; screenshots=${output}`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
