const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'en-US' });
    const target = process.env.DESKTOP_TEST_URL || 'http://127.0.0.1:18100/vnc.html?autoconnect=true&resize=scale';
    if (!['127.0.0.1', 'localhost'].includes(new URL(target).hostname)) throw new Error('Local desktop checks only');
    await page.goto(target, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.documentElement.classList.contains('noVNC_connected'), null, { timeout: 60000 });
    await page.waitForFunction(() => document.querySelector('#noVNC_container canvas')?.width >= 100, null, { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.locator('#noVNC_container canvas').click({ button: 'right' });
    await page.waitForTimeout(500);
    const pixels = await page.locator('#noVNC_container canvas').evaluate(canvas => {
      const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
      const samples = new Set();
      for (let i = 0; i < data.length; i += 400) samples.add(`${data[i]},${data[i + 1]},${data[i + 2]}`);
      return { width: canvas.width, height: canvas.height, colors: samples.size };
    });
    const output = path.resolve(__dirname, process.env.DESKTOP_SCREENSHOT || '../../outputs/computer-desktop-20261008.png');
    await page.screenshot({ path: output });
    if (pixels.width < 100 || pixels.height < 100 || pixels.colors < 2) throw new Error(`Desktop canvas is blank: ${JSON.stringify(pixels)}`);
    fs.writeFileSync(path.resolve(__dirname, '../../outputs/computer-desktop-check-20261008.json'), JSON.stringify(pixels, null, 2));
    console.log(JSON.stringify({ passed: true, ...pixels, screenshot: output }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
