import { chromium } from 'playwright';
import path from 'node:path';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails';
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on('console', m => console.log('PAGE:', m.text()));
page.on('requestfailed', req => console.log('FAIL:', req.url(), req.failure()?.errorText));
await page.goto('file://' + path.join(ROOT, 'render/captions.html'));
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });

const fontCheck = await page.evaluate(async () => {
  const fonts = [];
  document.fonts.forEach(f => fonts.push({ family: f.family, weight: f.weight, status: f.status }));
  const ok = await document.fonts.check('900 90px Montserrat');
  return { fonts, check: ok };
});
console.log('fonts:', JSON.stringify(fontCheck, null, 2));
await browser.close();
