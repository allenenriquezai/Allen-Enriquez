import { chromium } from 'playwright';
import path from 'node:path';

const ROOT = '/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails';
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on('console', m => console.log('PAGE:', m.text()));
await page.goto('file://' + path.join(ROOT, 'render/captions.html'));
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });

for (const t of [0.5, 5.0, 15.0, 33.0]) {
  await page.evaluate(t => window.__setTime(t), t);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const info = await page.evaluate(() => {
    const lines = document.querySelectorAll('.line');
    for (const L of lines) {
      if (L.classList.contains('visible')) {
        const words = Array.from(L.children).map(s => ({
          text: s.textContent,
          active: s.classList.contains('active'),
          hero: s.classList.contains('hero'),
          computedFont: getComputedStyle(s).fontFamily
        }));
        return { idx: L.dataset.idx, words };
      }
    }
    return null;
  });
  console.log('t=' + t, JSON.stringify(info, null, 2));
}
await browser.close();
