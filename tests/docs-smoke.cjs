const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const base = process.env.DOCS_TEST_URL || 'http://127.0.0.1:18110';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const missing = await browser.newContext();
    assert.equal((await missing.request.get(base + '/docs/missing-file.js')).status(), 404);
    const pdf = await missing.request.get(base + '/docs/download/manual.pdf');
    assert.equal(pdf.status(), 200);
    assert.ok((await pdf.body()).subarray(0, 5).equals(Buffer.from('%PDF-')));
    await missing.close();
    for (const width of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base + '/docs/', { waitUntil: 'networkidle' });
      await page.locator('.doc-body').waitFor();
      assert.ok(await page.locator('.doc-nav-group a').count() > 2);
      if (width < 600) await page.locator('.mobile-toc-toggle').click();
      await page.locator('.docs-search input').fill('API');
      await page.waitForTimeout(200);
      assert.ok(await page.locator('.doc-nav-group a').count() > 0);
      await page.locator('.docs-search input').fill('');
      await page.locator('.doc-nav-group a').nth(1).click();
      await page.waitForFunction(() => location.hash.length > 1);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('.doc-body').waitFor();
      assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.screenshot({ path: `outputs/docs-${width}.png`, fullPage: true });
      await page.close();
    }
    console.log('PASS docs desktop/mobile, chapters, search, deep links, PDF and missing-file 404');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
