const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const width of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto('http://127.0.0.1:18108/');
      await page.waitForFunction(() => document.querySelector('#containers').textContent.includes('singux-mysql-1'));
      assert.equal(await page.locator('#stages tr').count(), 5);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.locator('#refresh').click();
      await page.screenshot({ path: `outputs/migration-monitor-${width}.png`, fullPage: true });
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('PASS desktop/mobile, live containers, stages, refresh, no overflow or JS errors');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
