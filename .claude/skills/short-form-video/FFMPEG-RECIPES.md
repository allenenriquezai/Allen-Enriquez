# Short-Form Video — ffmpeg Recipes

**Load this file when:** iterating on text/sticker overlays on an already-rendered reel, OR the Hyperframes renderer produces a broken face (freezes / disappears in CTA window).

Use these paths INSTEAD of re-rendering the full Hyperframes composition. Full render = ~8 min on Mac. ffmpeg composite = <30 sec.

## Recipe 1 — Fast overlay iteration (Chrome headless PNG + ffmpeg)

When iterating on hook sticker copy, a pinned header, or any static text overlay, do NOT re-render the full Hyperframes composition.

1. Write the overlay as a standalone HTML file (`assets/<overlay>.html`) on `background: transparent`
2. Screenshot via headless Chrome:
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --headless=new --disable-gpu --hide-scrollbars \
     --default-background-color=00000000 \
     --window-size=<W>,<H> \
     --virtual-time-budget=4000 \
     --screenshot=assets/<overlay>.png \
     "file://$PWD/assets/<overlay>.html"
   ```
   The `--virtual-time-budget=4000` is **critical** — it gives Google Fonts time to load before capture. Without it you get empty boxes.
3. Composite onto the existing rendered video with ffmpeg:
   ```bash
   ffmpeg -y -i <rendered>.mp4 -i <overlay>.png \
     -filter_complex "[0:v][1:v]overlay=<X>:<Y>:enable='between(t,<T1>,<T2>)'[out]" \
     -map "[out]" -map 0:a -c:v libx264 -preset fast -crf 17 \
     -pix_fmt yuv420p -c:a aac -b:a 192k <final>.mp4
   ```

**Only fall back to Hyperframes re-render when the overlay needs animation** or is baked deep into a timeline-driven scene. Static text overlays = use this path always.

## Recipe 2 — Face + animation compositing (when renderer fails to embed face)

If the Hyperframes renderer produces a composition where the face disappears in the CTA window (ambient-bg / scene DOM lingers past its data-duration, or Chromium can't seek MOV past a certain point), use a three-input ffmpeg composite instead of re-rendering. Known-good pattern (from `projects/personal/videos/reel-3/`):

```bash
ffmpeg -y \
  -i assets/source.mp4 \               # input 0: face (base)
  -i renders/<overlay-only>.mp4 \      # input 1: animation layer rendered from Hyperframes
  -i assets/<hook-sticker>.png \       # input 2: hook sticker PNG
  -filter_complex "\
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setpts=PTS-STARTPTS[face];\
    [1:v]setpts=PTS-STARTPTS[anim];\
    [1:v]crop=1080:360:0:1560,setpts=PTS-STARTPTS[cap];\
    [face][anim]overlay=0:0:enable='between(t,<T_middle_start>,<T_middle_end>)'[step1];\
    [step1][cap]overlay=0:1560:enable='between(t,<T_cta_start>,<T_end>)'[step2];\
    [step2][2:v]overlay=<X>:<Y>:enable='between(t,0,<T_middle_start>)+between(t,<T_cta_start>,<T_end>)'[out]" \
  -map "[out]" -map 0:a \
  -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k \
  renders/<reel>-final.mp4
```

What it does:
- Face plays underneath the whole duration (source.mp4 is base)
- Animation overlays the face only during the middle window (scene overlays natively cover face there)
- Captions from the overlay render get cropped to bottom-360px and re-overlaid during CTA so captions stay visible with face showing
- Hook sticker PNG overlays on top during hook + CTA windows

Source `.mov` files may freeze mid-playback in Chromium; always transcode to `.mp4` first (`ffmpeg -i source.mov -c:v libx264 -crf 18 -c:a aac source.mp4`) before giving to Hyperframes OR ffmpeg.
