import { chromium } from 'playwright';
import path from 'node:path';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails';

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1080, height: 280 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
await page.goto('file://' + path.join(ROOT, 'render/header.html'));

// Wait for fonts
await page.evaluate(() => document.fonts.ready);
// Small settle delay for font paint
await page.waitForTimeout(250);

await page.screenshot({
  path: path.join(ROOT, 'render/header.png'),
  omitBackground: true,
  clip: { x: 0, y: 0, width: 1080, height: 280 },
  type: 'png'
});

await browser.close();
console.log('wrote', path.join(ROOT, 'render/header.png'));
