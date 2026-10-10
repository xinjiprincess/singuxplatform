const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:14000', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('#root')?.children.length > 0, null, { timeout: 60000 });
    await page.waitForTimeout(2000);
    const text = await page.locator('#root').innerText();
    if (!text.trim() || errors.length) throw new Error(JSON.stringify({ text, errors }));
    const screenshot = path.resolve(__dirname, '../../outputs/services-web-preview-20261009.png');
    await page.screenshot({ path: screenshot });
    console.log(JSON.stringify({ passed: true, screenshot, text: text.slice(0, 200) }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
