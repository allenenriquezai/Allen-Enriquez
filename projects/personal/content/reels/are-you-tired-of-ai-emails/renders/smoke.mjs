import { chromium } from 'playwright';
import path from 'node:path';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails';
const browser = await chromium.launch({ args: ['--disable-web-security'] });
const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on('console', msg => console.log('PAGE[' + msg.type() + ']:', msg.text()));
page.on('pageerror', err => console.log('PAGEERROR:', err.message));

const fileUrl = 'file://' + path.join(ROOT, 'design/project/AI Emails Reel.render.html');
await page.goto(fileUrl);
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });
await page.waitForTimeout(800);

// Sample a few times
for (const t of [0.5, 5, 15, 25, 35, 40]) {
  await page.evaluate(t => window.__setTime(t), t);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.screenshot({ path: path.join(ROOT, `render/smoke-t${t}.png`), clip: { x:0, y:0, width:1080, height:1920 } });
  console.log('wrote smoke-t' + t);
}
await browser.close();
console.log('done');
