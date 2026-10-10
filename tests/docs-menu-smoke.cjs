const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
(async () => {
  const password = process.env.SINGUX_TEST_PASSWORD;
  delete process.env.SINGUX_TEST_PASSWORD;
  assert.ok(password);
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    page.on('pageerror', e => console.log('Page error:', e.message));
    page.on('requestfailed', r => console.log('Request failed:', new URL(r.url()).pathname, r.failure()?.errorText));
    await page.goto((process.env.DOCS_TEST_URL || 'http://127.0.0.1:18109') + '/login', { waitUntil: 'networkidle' });
    await page.locator('input').filter({ visible: true }).first().fill('admin');
    await page.locator('input[type=password]').fill(password);
    await page.locator('button[type=submit]').click();
    await page.waitForURL(url => !url.pathname.endsWith('/login'), { timeout: 60000 });
    await page.locator('[class*="user-icon"], [data-testid="documentation-menu"]').first().waitFor({ timeout: 60000 });
    const directLink = page.getByTestId('documentation-menu');
    if (await directLink.count()) {
      const popupPromise = page.waitForEvent('popup');
      await directLink.click();
      const popup = await popupPromise;
      await popup.locator('.doc-body').waitFor({ timeout: 45000 });
      assert.equal(new URL(popup.url()).pathname, '/docs/');
      console.log('PASS authenticated source menu icon opens bundled same-origin documentation');
      return;
    }
    const icons = page.locator('[class*="user-icon"]');
    let clicked = false;
    for (let i = 0; i < await icons.count(); i++) {
      await icons.nth(i).hover();
      await page.waitForTimeout(400);
      if (await page.locator('.ant-tooltip-inner').filter({ hasText: /^文档$/ }).isVisible()) {
        await icons.nth(i).click();
        clicked = true;
        break;
      }
    }
    assert.ok(clicked, 'Documentation icon not found in the actual menu');
    await page.frameLocator('iframe').locator('.doc-body').waitFor({ timeout: 45000 });
    console.log('PASS authenticated target menu icon opens embedded same-origin documentation');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
