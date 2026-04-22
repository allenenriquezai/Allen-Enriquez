# Fast Render SOP — Composite Pipeline

Default for all reels. Beats single-pass hyperframes render by 3-5× without quality loss.

## Why

Hyperframes single-pass render captures EVERY element per frame via headless Chrome:
face video decode + scene animations + captions + fonts + glows. On 16GB RAM Mac
with `-w auto` (6 workers), this hangs. On `-w 2`, takes 7-10 min.

Composite pipeline splits the work:
- Hyperframes renders only what needs Chrome (animations, captions)
- ffmpeg stitches everything else (face decode, audio, overlays)

ffmpeg is near-realtime on modern Macs. Chrome capture is the bottleneck.

## The pipeline

```
source.mov (talking head + audio, full duration)
    │
    ├─ animation.mp4   ← hyperframes render (scenes only, no face, no audio)
    │                   covers black section (e.g. 6.70 → 54.22s)
    │
    ├─ captions.mov    ← hyperframes render --format=mov (transparent bg)
    │                   captions.html composition, full duration
    │
    └─ ffmpeg composite
          ├─ base:     source.mov (face + audio)
          ├─ overlay:  animation.mp4 on top during black window
          ├─ overlay:  captions.mov on top, full duration
          └─ audio:    passthrough from source.mov
        → final.mp4
```

## When to use

- ANY reel longer than 15s (below that, single-pass is fine)
- ANY reel with face video + scene animations + captions
- ANY reel where first render hung or took >5min

## Prerequisites

- `source.mov` in reel's `assets/` (talking head, full audio)
- `compositions/scene*.html` (scene animations built + lint-clean)
- `compositions/captions.html` with word-level SEGMENTS from transcript.json
- Black-section time bounds known (global start/end of animation window)

## Step 1 — Animation-only MP4

Use an index file that includes ONLY scenes (no face, no audio, no captions).
Save it as `index-animation.html`:

```html
<div id="root" data-composition-id="main"
     data-start="0" data-duration="<BLACK_DURATION>" ...>
  <!-- scenes back-to-back, track 5/6 alternating to avoid float overlap -->
  <div data-composition-id="scene1-xxx" data-composition-src="..." ...></div>
  ...
</div>
```

Render:
```bash
npx hyperframes render -o renders/animation.mp4 \
  -q standard -f 30 -w 2 \
  --entry index-animation.html
```

Expect ~1s of render per 1s of output on -w 2.

## Step 2 — Captions-only MOV (transparent)

Save a `index-captions.html` with ONLY the captions composition, full duration:

```html
<div id="root" data-composition-id="main"
     data-start="0" data-duration="<TOTAL_DURATION>" ...>
  <div data-composition-src="compositions/captions.html"
       data-start="0" data-duration="<TOTAL>" data-track-index="20"></div>
</div>
```

Render as MOV for alpha channel:
```bash
npx hyperframes render -o renders/captions.mov \
  --format=mov -q standard -f 30 -w 2 \
  --entry index-captions.html
```

MOV with alpha = transparent background → overlays cleanly without needing chroma key.

## Step 3 — ffmpeg composite

Variables:
- `BLACK_START` = animation window start (e.g. 6.70)
- `TOTAL` = full reel length (e.g. 56.46)

```bash
ffmpeg -y \
  -i assets/source.mov \
  -itsoffset <BLACK_START> -i renders/animation.mp4 \
  -i renders/captions.mov \
  -filter_complex "\
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[base]; \
    [base][1:v]overlay=enable='between(t,<BLACK_START>,<BLACK_END>)'[bg]; \
    [bg][2:v]overlay=0:0[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -preset medium -crf 18 \
  -c:a copy \
  -r 30 -t <TOTAL> \
  renders/final.mp4
```

Key flags:
- `-itsoffset <BLACK_START>` shifts animation.mp4 to start at black-section global time
- `overlay=enable='between(t,...)'` only renders animation during that window
- `captions.mov` overlays full duration (alpha channel handles transparency)
- `-t <TOTAL>` clamps output to exact reel length
- `-crf 18` = visually lossless. Drop to 20-23 for smaller files if needed.
- `-c:a copy` — NEVER re-encode audio. AAC re-encode causes doubled/phased voice artifact.

## Step 4 — Verify

```bash
ffprobe -v error -show_entries format=duration,bit_rate \
  -of default=noprint_wrappers=1 renders/final.mp4
open renders/final.mp4
```

Check: duration matches `TOTAL`, audio present, captions legible, animation overlays clean.

## Header Pill Overlay

Static title card over talking-head sections (hook + CTA). Render once as PNG, ffmpeg overlay per reel.

### Rules (locked from 7-things reel)
- **Position:** `top: 300px` — mid-upper screen, close to face for TikTok visual zone. Not at the very top (too far from head).
- **Show:** hook start → hook end AND CTA start → reel end
- **CTA start** = timestamp of first CTA word in transcript (find via captions.html SEGMENTS search for "pick" or first CTA keyword). Animation overlay must ALSO end at CTA start — don't let scenes cover the face during CTA.
- **Never show** during scene overlay window (hook_end → cta_start)

### Generate header PNG
```bash
python3 - <<'EOF'
from playwright.sync_api import sync_playwright
import pathlib
html_path = pathlib.Path("compositions/header.html").resolve()
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--enable-transparent-background"])
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    page.goto(f"file://{html_path}")
    page.wait_for_timeout(2000)
    page.screenshot(path="renders/header.png", full_page=False, omit_background=True)
    browser.close()
EOF
```

### ffmpeg composite with header (replace Step 3)

Variables: `HOOK_END`, `CTA_START`, `TOTAL`

```bash
ffmpeg -y \
  -i assets/source.mov \
  -itsoffset <HOOK_END> -i renders/animation.mp4 \
  -i renders/captions.mov \
  -i renders/header.png \
  -filter_complex "\
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[base]; \
    [base][1:v]overlay=enable='between(t,<HOOK_END>,<CTA_START>)'[bg]; \
    [bg][2:v]overlay=0:0[bgc]; \
    [3:v]format=rgba[hdr]; \
    [bgc][hdr]overlay=0:0:enable='lte(t,<HOOK_END>)+gte(t,<CTA_START>)'[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -preset medium -crf 18 \
  -c:a copy \
  -r 30 -t <TOTAL> \
  renders/final.mp4
```

Key: `lte(t,HOOK_END)+gte(t,CTA_START)` = ffmpeg OR expression for header enable window.
Animation `between(t,HOOK_END,CTA_START)` — ends at CTA start, not at animation track end.

### Header pill style (compositions/header.html)
- Dark navy `#05080F` pill, `border: 3px solid #02B3E9`, `border-radius: 60px`
- Cyan glow: `box-shadow: 0 0 18px 4px rgba(2,179,233,0.55), 0 0 40px 10px rgba(2,179,233,0.25)`
- Text: Montserrat 900, 46px, uppercase, white + cyan text-shadow
- Width: 960px centered, `top: 300px`

---

## Retime (Allen edits audio after render)

1. Re-transcribe new source with `tools/transcribe_video.py`
2. Regenerate captions.html SEGMENTS from new word timings
3. Re-render captions.mov only (~40s)
4. If black-section bounds changed → re-render animation.mp4
5. Re-composite via Step 3

Never touch scenes unless bounds move. Captions re-render is almost free.

## Fallback: single-pass if composite fails

If ffmpeg errors or composite looks off:
```bash
npx hyperframes render -o renders/full.mp4 -q standard -f 30 -w 2
```
Close VS Code, Dialpad, other apps first. Expect 7-10min on 16GB RAM Mac.

## Benchmarks (7-things reel, 56.46s)

| Method | Time | RAM peak | Hang? |
|---|---|---|---|
| Single-pass `-w auto` | killed | ~12GB | yes |
| Single-pass `-w 2` | 7-10min | ~4GB | no |
| Composite pipeline | ~2min total | ~3GB | no |

## Related

- `tools/transcribe_video.py` — word-level timings for captions SEGMENTS
- `.claude/skills/scene-animation/TRANSCRIBE.md` — transcription SOP
- `.claude/skills/scene-animation/SKILL.md` — scene authoring (step 1 of pipeline)
- Memory: `project_reel_speed_target.md` — 20-min reel target that this SOP serves
- Memory: `feedback_overlay_png_chrome_headless.md` — prior-art for the composite pattern
