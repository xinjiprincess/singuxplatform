const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const width of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto('http://127.0.0.1:18109/login', { waitUntil: 'networkidle', timeout: 60000 });
      assert.ok(await page.locator('input').count() >= 2, 'Login inputs missing');
      assert.equal(await page.evaluate(() => document.body.innerText.trim().length > 20), true);
      await page.screenshot({ path: `outputs/migration-app-login-${width}.png`, fullPage: true });
      assert.deepEqual(errors, [], 'Login runtime errors');
      console.log(JSON.stringify({ width, loginRendered: true, pageErrors: errors.length,
        horizontalOverflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth) }));
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
