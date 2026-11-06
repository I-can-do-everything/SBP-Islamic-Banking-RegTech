// Renders each HTML file in this folder to a PNG one level up, at 2x scale.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 675 }, deviceScaleFactor: 2 });
  for (const name of process.argv.slice(2)) {
    await page.goto('file://' + path.resolve(__dirname, name + '.html'));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.resolve(__dirname, '..', name + '.png') });
    console.log('rendered', name);
  }
  await browser.close();
})();
