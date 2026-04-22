import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-4-are-you-tired-of-ai-emails';
const FPS = 30;
const DURATION = 42;
const FRAMES = FPS * DURATION;
const FRAME_DIR = path.join(ROOT, 'render/frames-transparent');
fs.mkdirSync(FRAME_DIR, { recursive: true });

const browser = await chromium.launch({ args: ['--disable-web-security'] });
const ctx = await browser.newContext({
  viewport: { width: 1080, height: 1920 },
  deviceScaleFactor: 1,
  colorScheme: 'dark',
});
const page = await ctx.newPage();

page.on('console', msg => console.log('PAGE[' + msg.type() + ']:', msg.text()));
page.on('pageerror', err => console.log('PAGEERROR:', err.message));

const fileUrl = 'file://' + path.join(ROOT, 'design/project/AI Emails Reel.transparent.html');
console.log('loading', fileUrl);
await page.goto(fileUrl);
console.log('waiting for __ready');
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });
console.log('ready');

// Give fonts & first paint a moment
await page.waitForTimeout(500);

const startTs = Date.now();
for (let i = 0; i < FRAMES; i++) {
  const t = i / FPS;
  await page.evaluate(t => window.__setTime(t), t);
  // Two rAFs to settle React re-render after setState
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.screenshot({
    path: path.join(FRAME_DIR, 'f' + String(i).padStart(5, '0') + '.png'),
    clip: { x: 0, y: 0, width: 1080, height: 1920 },
    omitBackground: true,
  });
  if (i % 60 === 0) {
    const elapsed = ((Date.now() - startTs) / 1000).toFixed(1);
    console.log('frame', i, '/', FRAMES, 'elapsed', elapsed + 's');
  }
}

await browser.close();
console.log('done');
