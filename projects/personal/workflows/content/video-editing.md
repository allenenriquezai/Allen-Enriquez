# Video Editing SOP

Edit raw footage into Hormozi-style videos. Reels (30-60s, 9:16) and YouTube (7-12min, 16:9).

## Two pipelines — pick the right one

| Pipeline | When | Tool |
|---|---|---|
| **Python pipeline** (default) | Plain talking-head reels. Cuts, captions, zooms, music. Fast. | `tools/personal/edit_video.py` (FFmpeg + Whisper) |
| **Hyperframes** (motion-graphic overlays) | Brand intros/outros, scene transitions, animated stats, lower-thirds, karaoke captions, "Nate Herk" style | `npx hyperframes` (HTML + GSAP + Puppeteer) |

Rule of thumb: if it's a straight talking-head → Python. If it needs branded motion graphics on top → Hyperframes (or Hyperframes does the whole thing).

## Style

Primary: Alex Hormozi -- raw, educational, value-first. Borrow punch-in zooms and clean sound design from Iman Gadzhi. NOT lifestyle/luxury content.

## Setup

1. Read style guide: `projects/personal/reference/hormozi-style-guide.md`
2. Check deps: `python3 tools/personal/edit_video.py check-deps`
3. If SFX missing: `python3 tools/personal/edit_video.py generate-sfx`

## Workflow

Present options at each step. Never auto-decide without showing Allen.

### Step 1 -- Transcribe

```bash
python3 tools/personal/edit_video.py edit --input "<path>" --type <reel|youtube> --captions off --no-zoom 2>&1 | head -30
```
Or transcribe only:
```bash
whisper "<path>" --model base --output_format json --output_dir .tmp/videos/
```

Show Allen the transcript. Ask: sections to cut? Sections to keep? Key points for zoom emphasis?

### Step 2 -- Edit Plan

Present:
- **Cuts:** Silence/filler to remove. Content sections at risk.
- **Zooms:** 3-5 moments for punch-in (100% to 120%). Bold claims, numbers, takeaways.
- **B-roll:** Every 15-30s, suggest inserts. Identify "concept explanation" moments needing doodle explainers. Screenshots/screen recordings at timestamps.
- **Captions:** Anton font, uppercase, white + yellow keyword highlight. Flag emphasis words.
- **SFX:** Whoosh on transitions, pop on text, background music (-20dB).

Allen picks what to keep, cut, or change.

### Step 3 -- Generate Doodle B-roll

For approved concept moments:
1. Describe the concept simply
2. Use Excalidraw to generate whiteboard-style doodles
3. Save PNGs to `.tmp/videos/<slug>/broll/`
4. Style: $100M Offers book illustrations -- stick figures, hand-drawn boxes, arrows, minimal color

### Step 4 -- Execute Edit

```bash
python3 tools/personal/edit_video.py edit \
  --input "<path>" \
  --type <reel|youtube> \
  --style hormozi \
  --captions on \
  --music "<music_path>" \
  --broll ".tmp/videos/<slug>/broll/" \
  --whisper-model base
```

### Step 5 -- Review Output

Show Allen: before/after duration, file size, final video path, timeline.md, edit_log.json.

Ask: anything to re-cut? Caption timing? Sections to change?

If changes needed, adjust and re-run specific steps.

## Editing Techniques

| Technique | Reel | YouTube |
|---|---|---|
| Silence removal | Cut pauses > 0.4s, all filler | Same but preserve breathing between sections |
| Captions | Always on. Anton, uppercase, white + yellow highlight, word-by-word | Optional. Enable for accessibility. |
| Punch-in zoom | 100% to 120% over 3-5s on key points. Hard cut back. | Same, 3-5 per video. Don't overuse. |
| B-roll | N/A | Doodle explainers every 15-30s. Screenshots at timestamps. |
| Text overlays | Key numbers, max 5 words | Numbered frameworks, concept reinforcement, chapter markers |
| Transitions | Hard cuts. White flash between sections. | Hard cuts. White flash. Crossfade for chapter breaks. |
| SFX | Whoosh, pop, music at -20dB | Same. Music rises during B-roll. |
| Color | Saturation 1.3x, contrast 1.1x, brightness +0.05 | Same |
| Pacing | Aggressive. 1 idea per 10s. No pauses. | Medium. 1 idea per 60-90s. Breathe between sections. |

## Output

All files to `.tmp/videos/<slug>/`. Keep intermediate files (trimmed.mp4, captions.ass) for re-editing.

## Rules

- NEVER auto-edit without showing Allen the plan first.
- NEVER skip the transcript review step.
- If a step fails, show the error and suggest a fix. Don't retry silently.
- Reels: prioritize speed and punchiness. Cut aggressively.
- YouTube: preserve breathing room. Cut filler, keep natural pacing.
- Doodle B-roll should TEACH, not decorate. Every insert explains a concept.

---

## Hyperframes Pipeline (motion graphics)

HTML-based video framework. Compositions are HTML + GSAP timelines. CLI handles preview + render + transcribe + TTS. Agent-driven: Claude writes the composition, Hyperframes renders it.

### When to use
- Short-form reels with motion-graphic overlays on talking-head (Nate Herk / May Shorts 19 style)
- Brand intros/outros with AE logo + blue glow
- Animated stats, lower-thirds, karaoke captions, scene transitions
- Shorts built from scratch without footage (title cards, explainers, promos)
- Website → video promos (`/website-to-hyperframes`)

### Install status
- Global skills installed: `/hyperframes`, `/hyperframes-cli`, `/gsap`, `/hyperframes-registry`, `/website-to-hyperframes`, `/make-a-video`, `/short-form-video`
- Reference kit: `projects/personal/reference/hyperframes-student-kit/` — 12 finished projects to study (may-shorts-18/19 = short-form vertical playbook)
- Working directory: `projects/personal/videos/` — Allen's own projects go here

### Workflow

**New video from scratch (beginner path):**
1. Invoke `/make-a-video` — skill interviews Allen, builds the full MP4 end-to-end
2. Review, iterate, render final

**New short-form reel (structured path):**
1. Record talking head (9:16 or native 16:9 for face-mode choreography)
2. `cd projects/personal/videos && npx hyperframes init <slug>`
3. Invoke `/short-form-video` — encodes the full May Shorts 19 playbook (4-layer scaffold: ambient-bg, face, scene overlays, captions)
4. Transcribe: `npx hyperframes transcribe <edit>.mp4 --model small.en --json`
5. Preview: `npx hyperframes preview` (http://localhost:3002, hot-reload)
6. Lint → draft render → frame verify → final render

**Core CLI commands (see `/hyperframes-cli`):**
```bash
npx hyperframes init <slug>        # scaffold project
npx hyperframes preview            # browser preview w/ hot-reload
npx hyperframes lint               # validate composition
npx hyperframes transcribe <file>  # whisper transcript + karaoke timing
npx hyperframes tts <text>         # generate voiceover
npx hyperframes render             # MP4 output
npx hyperframes doctor             # troubleshoot env
```

### Brand application

Every Hyperframes composition for Allen MUST apply the AE brand system (see `project_brand_visual_system` memory + `projects/personal/brand/brand-guidelines.png`):
- Primary blue `#02B3E9` on accents, buttons, active states
- Dark navy near-black backgrounds with subtle radial blue glow
- Roboto Mono Medium for stats/UI/numbers, Montserrat Light for body
- AE monogram on intro/outro (top-left when nav present, centered on title cards)
- White captions + yellow keyword highlight (keep Hormozi caption rule)

### Hybrid with Python pipeline

For talking-head-primary reels: cut + caption + zoom in Python, export clean MP4, then drop into a Hyperframes composition for branded intro/outro + lower-thirds. Don't double-caption.

### Reference projects to study

Short-form vertical (9:16, what Allen will ship most):
- `may-shorts-19`, `may-shorts-18` — face-mode choreography + synced scene overlays + karaoke captions

Landscape + promos:
- `may-shorts-6` (16:9), `linear-promo-30s`, `first-agent-promo`, `clickup-demo`

Educational:
- `aisoc-lesson-5-1`, `golden-ratio-demo`, `claude-edit-intro`

---

## AE Short-Form Reel Recipe (locked — apply to every reel)

Battle-tested on `projects/personal/videos/reel-2/` (What Is an AI Agent). Reuse the full stack below on every new reel. Don't re-invent.

### Project scaffold
```
projects/personal/videos/reel-N/
├── hyperframes.json           # registry + paths
├── meta.json                  # 1080x1920, 60fps (or 30 for draft)
├── index.html                 # root composition, duration = full source video
├── assets/hook-sticker.png    # brand hook banner (generated by Pillow)
├── compositions/
│   ├── ambient-bg.html        # dark navy + blue glow orbs + grid floor (only during middle)
│   ├── scene1-<label>.html    # ONE per script beat (4-7 beats per reel)
│   ├── …
│   └── captions.html          # karaoke, FULL 55s duration, source-time timings
└── renders/
    ├── overlay-v2.webm        # Hyperframes output (captions + middle scenes)
    └── final-v3.mp4           # ffmpeg composite with face + sticker
```

### Source video analysis (always first)
1. `ffprobe` source for duration, resolution, fps.
2. `ffmpeg blackdetect=d=0.5:pix_th=0.10` to find black segments (voiceover-only zones).
3. `npx hyperframes transcribe <source> --model small.en --json` → word-level timestamps.
4. Scene design: one sub-composition per natural phrase boundary (pauses >300ms or topic shifts). Target 2-10s per beat.

### Hook Sticker (top banner on face segments)
**Design:** Dark panel + brand-blue border + blue glow + white Montserrat 900.
**Shows on:** face segments only (hook + CTA). Hidden during animation middle where scenes carry the message.
**Position:** y=160, centered horizontally.
**Generator:** Pillow script (920×340 canvas, inner 960×220 with 60px glow padding, 86pt 2-line font for bold presence without overflow). Save to `assets/hook-sticker.png`.

**Exact CSS spec** (locked — use on every reel):
- Container: `background: #071020`, `border: 5px solid #02B3E9`, `border-radius: 36px`
- Glow: `box-shadow: 0 0 28px rgba(2,179,233,0.85), 0 0 64px rgba(2,179,233,0.50), 0 10px 26px rgba(0,0,0,0.55)`
- Text: Montserrat 900, UPPERCASE, white, layered black text-shadow stroke (`-3/3/3/3` offsets + `0 6px 18px rgba(0,0,0,0.7)` drop)
- Text wrap: `white-space: nowrap` each line + tune font-size so each line fits (54–64px for 800px wide sticker)
- Reference working file: `projects/personal/videos/reel-3/assets/pin-note.html` (filename says pin-note, it IS the hook sticker)
- **Do NOT** use yellow Post-it / sticky-note styling — rejected. Dark pill + cyan glow only.

Prompt template per reel: one punchy line, 2 words × 2 lines max. Examples:
- "YOU'RE USING / AI WRONG" (AI agents reel)
- "STOP CHASING / PERFECTION" (productivity reel)
- "YOUR COMPETITOR / HAS ONE" (urgency reel)

Sizing rule: text width must fit inner box width × 0.95. If longer → drop font size by 10pt or split lines.

### Karaoke Captions (full-duration, source-time)
**Pattern:** Adapt may-shorts-19 `compositions/captions.html`.
**Word list:** ALL words from transcript (face + animation + CTA), in SOURCE time (no shift).
**Corrections:** Fix whisper errors (Cloud → Claude, merge "chat GPT" → "ChatGPT").
**Segments:** Group words into ≤7-word phrases, break on pauses >500ms.
**Timing rule — sequential, not overlapping:** Each segment hides at NEXT segment's start (hard swap, 0.05s fade). Do NOT use pre-roll/post-hold fades — they stack visually on packed voiceovers.
**Style:** Montserrat 900 68pt, uppercase, 4px black text-shadow stack. Active word: `#02B3E9` (brand blue) + 1.16 scale pop. Rest: white.
**Position:** `bottom: 280px`.

### Scene Composition Rules
- **Center content vertically.** Use `justify-content: center` on `.wrap`, not top-padding. Otherwise content drifts up and looks unbalanced on 9:16.
- **One idea per beat.** Don't stack sub-concepts in a single scene — split into next scene.
- **Brand palette only:** `#02B3E9` accent on active cards/text, white on hero text, `#FF3B30` only for urgency/negative framings. No other colors.
- **Typography:** Montserrat 800-900 for titles, Roboto Mono 500-700 for UI/data/captions-supporting.
- **Background:** dark navy `#05080F` with blue glow radial. Grid floor from MOTION_PHILOSOPHY (optional on lighter scenes).
- **Entry/exit transitions:** `y:150 + blur(30px) + opacity:0` in, `y:-150 + blur(30px) + opacity:0` out, `power3.out` / `power2.in`, ~0.33-0.55s. (NOTE: blur filter drops renders into slow screenshot mode — see Speed section.)

### Index.html Root Pattern (55s+ reels)
```html
<!-- Root duration = full source video duration -->
<div data-composition-id="main" data-duration="55.56" ...>
  <!-- Ambient bg: ONLY during animation middle (face shows at bookends) -->
  <div data-composition-src="compositions/ambient-bg.html"
       data-start="8.87" data-duration="43.53" data-track-index="1"></div>

  <!-- Scenes: data-start in SOURCE time (shifted by hook duration) -->
  <div data-composition-src="compositions/scene1-<label>.html"
       data-start="8.87" data-duration="3.53" data-track-index="5"></div>
  <!-- …repeat for each beat… -->

  <!-- Captions: FULL source duration with source-time word list -->
  <div data-composition-src="compositions/captions.html"
       data-start="0" data-duration="55.56" data-track-index="20"></div>

  <!-- Vignette: only during middle -->
  <div id="top-vignette" class="clip" data-start="8.87" data-duration="43.53" data-track-index="25"></div>
</div>
```

`html, body { background: transparent; }` so face bleeds through at bookends.

### Render + Composite Recipe
```bash
# From inside projects/personal/videos/reel-N/
npx --prefix ../../reference/hyperframes-student-kit hyperframes lint
npx --prefix ../../reference/hyperframes-student-kit hyperframes render \
  --quality draft --format webm --output renders/overlay-v2.webm

# Composite: face base + chroma-key overlay + hook sticker on face segments
ffmpeg -y -threads 10 \
  -i "<source>.mov" \
  -i renders/overlay-v2.webm \
  -i assets/hook-sticker.png \
  -filter_complex "
    [0:v]scale=1080:1920,fps=30,setpts=PTS-STARTPTS[face];
    [face]split=2[face_hook][face_cta];
    [face_hook]trim=0:<hook-end>,setpts=PTS-STARTPTS[f_hook];
    [face_cta]trim=<anim-end>:<src-end>,setpts=PTS-STARTPTS[f_cta];
    [1:v]setpts=PTS-STARTPTS,split=3[ov1][ov2][ov3];
    [ov1]trim=0:<hook-end>,setpts=PTS-STARTPTS,colorkey=0x000000:0.10:0.05[ov_hook];
    [ov2]trim=<anim-end>:<src-end>,setpts=PTS-STARTPTS,colorkey=0x000000:0.10:0.05[ov_cta];
    [ov3]trim=<hook-end>:<anim-end>,setpts=PTS-STARTPTS[ov_mid];
    [f_hook][ov_hook]overlay=0:0:eof_action=pass[hook];
    [f_cta][ov_cta]overlay=0:0:eof_action=pass[cta];
    [hook][ov_mid][cta]concat=n=3:v=1:a=0[pre_outv];
    [pre_outv][2:v]overlay=x=(W-w)/2:y=160:enable='between(t,0,<hook-end>)+between(t,<anim-end>,<src-end>)'[outv]
  " \
  -map "[outv]" -map 0:a \
  -c:v libx264 -preset medium -crf 18 -threads 10 \
  -c:a aac -b:a 192k \
  renders/final.mp4
```

The chroma-key works because index.html has transparent body — face zones in the webm are pure black. Middle zones have scene content and play through directly.

### Speed / Render Mode Rules
Hyperframes drops to **slow screenshot mode** (5x slower) when any of these appear in scripts:
- `filter: blur(...)` tweens (not a supported GSAP property for its native timing)
- `filter: any()` tweens
- `onUpdate:` callbacks (trigger rAF ticker)
- `color` / `backgroundColor` tweens (mostly unsupported — use opacity on layered elements instead)
- `boxShadow` tweens
- `className` tweens
- `backgroundPositionY` tweens
- Any `gsap.ticker` or raw `requestAnimationFrame` usage

Supported fast-mode properties (ONLY these): `opacity, x, y, scale, scaleX, scaleY, rotation, width, height, visibility`.

**To keep fast render mode:**
- Replace blur entrance/exit with `scale + opacity` + `y` shift
- Replace typewriter `onUpdate` with per-character `<span>`s animated by opacity stagger
- Replace color karaoke pops with STACKED dim + active word spans, animate opacity
- Replace boxShadow glow with a sibling `.glow` div + opacity tween
- Replace className toggle with a sibling `.active-indicator` div + opacity

Non-fast-mode renders ~8 min for 55s. Fast mode ~1.5 min. Use `--workers 10` regardless.

### Known Iterate Items (fix in v4 when we have bandwidth)
- Scenes are "clean motion" not "Nate Herk kinetic." No whip transitions, no chrome gradient text, no camera dollies. OK for educational content; upgrade for brand hype reels.
- No visual callbacks (elements returning later). Add for premium feel.
- Scene duration avg 5s vs Nate ~1.5s. Fine for teaching; punchier for hype.
- Hold the CTA face 4+s for classic outro land. Current ~3s.

### Review Gate (mandatory)
After draft render:
1. Extract frames at each beat boundary: `ffmpeg -ss <t> -i draft.mp4 -frames:v 1 frame_<t>.png`
2. Read frames visually — confirm: no caption stacking, no text overflow, scene timings align with voiceover.
3. Only then run final render + ship.

### Face Visibility Rule
Allen's face MUST stay visible on the hook (first ~5–6s) and CTA (last ~13s). Scene overlays replace the face only in the middle (teaching/explain sections). Never cover the face during hook or CTA — personal connection at the open grabs attention, face at the close builds trust for the ask.

### Third-Party Proof — Blur Faces
When showing third-party people/companies as social proof (e.g., a screenshot of someone else's result), **blur the person's face/photo** (GaussianBlur radius 20 on photo regions). Keep headlines and stat numbers sharp — the stat matters, not the person. Avoids appearing to endorse or promote specific third parties.

### Caption Emphasis
"FREE" always capitalized in karaoke captions when Allen says "for free" — brand rule, emphasizes the value offer.
