const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const base = process.env.DOCS_TEST_URL || 'http://127.0.0.1:18110';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(base + '/docs/');
    await page.locator('.reader-actions').waitFor();
    await page.evaluate(() => {
      document.body.replaceChildren();
      const frame = document.createElement('iframe');
      frame.src = '/docs/';
      frame.allowFullscreen = true;
      frame.style.cssText = 'position:fixed;left:220px;top:0;width:calc(100% - 220px);height:100%;border:0';
      document.body.append(frame);
    });
    const frame = page.frameLocator('iframe');
    await frame.locator('.doc-body').waitFor();
    assert.equal(await frame.locator('.public-nav').isVisible(), false);
    assert.ok(await frame.locator('.doc-body').evaluate(e => parseFloat(getComputedStyle(e).fontSize)) >= 15);
    assert.ok(await frame.locator('.docs-main').evaluate(e => e.getBoundingClientRect().width) > 700);
    await frame.locator('.doc-nav-group a').nth(1).click();
    const popupPromise = page.waitForEvent('popup');
    await frame.getByRole('button', { name: '独立窗口阅读' }).click();
    const popup = await popupPromise;
    await popup.locator('.doc-body').waitFor();
    assert.ok(new URL(popup.url()).hash);
    assert.equal(await popup.locator('.public-nav').isVisible(), true);
    assert.deepEqual(errors, []);
    await page.screenshot({ path: 'outputs/docs-reader-embedded.png', fullPage: true });
    console.log('PASS embedded readable layout, compact header, independent reading and chapter preservation');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
