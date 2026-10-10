const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const base = 'https://www.ciyuancenter.cc';
  const checks = [];
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    fs.mkdirSync('outputs/filing-production-20261009', { recursive: true });
    for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
      await page.setViewportSize({ width, height });
      for (const route of ['/login', '/space/1/develop', '/system/user']) {
        await page.goto(base + route, { waitUntil: 'domcontentloaded', timeout: 90000 });
        const footer = page.locator('#singux-site-filing');
        await footer.waitFor({ state: 'visible' });
        assert.equal(await footer.count(), 1);
        assert.equal(await footer.getByRole('link', { name: '蜀ICP备2026030409号' }).getAttribute('href'), 'https://beian.miit.gov.cn/');
        assert.equal(await footer.getByRole('link', { name: '公安备案查询' }).getAttribute('href'), 'https://beian.mps.gov.cn/#/query/webSearch');
        await page.waitForTimeout(1500);
        const bounds = await footer.boundingBox();
        assert.ok(bounds && bounds.x >= -1 && bounds.x + bounds.width <= width + 1);
        assert.ok(Math.abs(bounds.y + bounds.height - height) <= 1);
        const root = await page.locator('#root').boundingBox();
        assert.ok(root && root.y + root.height <= bounds.y + 1, 'Footer must reserve content space');
        checks.push({ viewport: name, requestedRoute: route, actualPath: new URL(page.url()).pathname, footer: bounds });
      }
      await page.screenshot({ path: `outputs/filing-production-20261009/${name}.png` });
    }
    fs.writeFileSync('outputs/filing-production-20261009/browser-check.json', JSON.stringify({ passed: true, authenticatedPagesTested: false, checks }, null, 2));
    console.log(JSON.stringify({ passed: true, checks: checks.length, authenticatedPagesTested: false }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
