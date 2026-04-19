import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails';
const FPS = 30, DURATION = 62.04, FRAMES = Math.ceil(FPS * DURATION);
const FRAME_DIR = path.join(ROOT, 'render/caption-frames');
fs.mkdirSync(FRAME_DIR, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on('console', m => console.log('PAGE:', m.text()));
await page.goto('file://' + path.join(ROOT, 'render/captions.html'));
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });

const t0 = Date.now();
for (let i = 0; i < FRAMES; i++) {
  const t = i / FPS;
  await page.evaluate(t => window.__setTime(t), t);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.screenshot({
    path: path.join(FRAME_DIR, 'c' + String(i).padStart(5, '0') + '.png'),
    omitBackground: true,
    clip: { x: 0, y: 0, width: 1080, height: 1920 }
  });
  if (i % 60 === 0) {
    const elapsed = (Date.now() - t0) / 1000;
    console.log('caption frame', i, '/', FRAMES, 'elapsed', elapsed.toFixed(1) + 's');
  }
}
await browser.close();
console.log('done');
