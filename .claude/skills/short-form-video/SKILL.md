---
name: short-form-video
description: Build and iterate short-form vertical (9:16) videos in Hyperframes — TikTok/Reels/Shorts style. Use when Allen says "short-form video", "vertical video", "TikTok/Reels/Shorts", "make a short", "talking-head + motion graphics", or when the target is a 1080x1920 composition with face video + synced scene overlays + karaoke captions. Encodes face-mode choreography, audio-synced scene timing, karaoke captions, and the 10-rule quality checklist.
---

# Short-Form Vertical Video (Hyperframes)

Short-form = 1080x1920 vertical, 10–30s, talking-head face + motion-graphic scene overlays + karaoke captions.

**Always invoke `/hyperframes` first.** This skill sits on top of it — framework rules (`data-*` attributes, `window.__timelines`, composition structure) are non-negotiable.

## Reference files — load only when situation matches

- **First build of a new reel, or reel "feels rigid/bland"** → read `LESSONS.md` (may-shorts-18 v1→v2 autopsy: slam timing, BOTTOM scale, face transitions, data-feel scenes)
- **Retime task or audio re-edited** → read `RETIME.md` (audio-sync protocol, retime table format)
- **Renderer fails / overlay iteration on rendered reel** → read `FFMPEG-RECIPES.md` (Chrome headless PNG + 3-input face composite)
- **Hook sticker design/edit** → read `HOOK-STICKER.md` (exact spec: dark pill + cyan border + white uppercase)
- **Render speed / pipeline** → read `RENDER.md` (composite vs single-pass, Mac render budget)

Do not load these preemptively. Only when the situation actually matches.

## GATE 0 — Animation Lock (BLOCKING, before anything else)

Before face / audio / captions / ambient-bg work: **all scene animations MUST be scrub-approved via `/scene-animation`**. Full Hyperframes render on Mac = ~8 min. Animation tweaks after face+audio+captions are layered cost a full re-render.

**Check:** Does `compositions/scene*.html` exist AND has Allen scrub-approved each one at `localhost:3002?comp=<id>`?

- **No** → STOP. Run `/scene-animation` first. Return here only when scenes locked.
- **Yes** → proceed.

## When this skill fires

- "Make a short-form video", "TikTok post", "Reels", "Shorts", "vertical video"
- Any build starting from talking-head recording + script/transcript for social
- Retiming, recutting, or re-syncing an existing short
- Adding karaoke captions synced to a voiceover

## The playbook (high-level)

1. **Audio is source of truth.** Edit audio FIRST (cut retakes, pauses). Save as `<name>-edit.mp4`. Measure exact duration with `ffprobe` — this is the composition's `data-duration`.
2. **Transcribe the edited audio** with `npx hyperframes transcribe <edit>.mp4 --model small.en --json`.
3. **Author scene boundaries in edited-time** — NEVER mix original-time and edited-time. See `RETIME.md` if editing an existing reel.
4. **Build the composition scaffold** (4 layers: ambient-bg, seam-treatment, captions, face).
5. **Author scenes with LOCAL offsets** relative to each scene's `data-start`. Each scene = `compositions/scene<N>-<label>.html`.
6. **Lint → draft render → word-exact frame verification → final render.** Never skip frame verification.

**Render speed gate:** Default = COMPOSITE PIPELINE, not single-pass. See `RENDER.md`. Single-pass `-w auto` hangs 16GB Macs.

## Composition scaffold (the 4 always-on layers)

```
index.html (root, 1080x1920, data-composition-id="main")
├── ambient-bg.html        track-index="3" — radial gradient + drift grid + particles + vignette
├── face-wrapper + <video> track-index="0" — talking head (see face-mode choreography)
├── seam-treatment.html    track-index="5" — feathers y=960 edge (bottom-half scenes only)
├── scene1-<label>.html    track-index="1" — scene overlays (back-to-back, no gaps)
├── scene2-<label>.html    track-index="1"
├── …
└── captions.html          track-index="2" — karaoke captions, word-synced
```

- `data-duration` identical across root, ambient-bg, seam-treatment, face-video, face-audio, captions. Only scene overlays change.
- `<audio>` for the face is SEPARATE (mixer needs it), never the video's own audio track.
- `class="clip"` goes on timed divs — NEVER on `<video>` or `<audio>`.

## Face-mode choreography (signature move)

Face lives in a wrapper div sized at source's native landscape (1920x1080). GSAP animates the WRAPPER (never the video element — animating `<video>` dimensions freezes frames).

```js
const BOTTOM     = { x: 0,       y: 1136, scale: 0.5625 }; // bottom-half, full landscape visible
const FULLSCREEN = { x: -1166.5, y: 0,    scale: 1.7778 }; // cropped-cover, fills 1080x1920
const MODE_DUR = 0.32;
```

**Transition 0.15s BEFORE the new scene's content lands**, `ease: "expo.inOut"`:

```js
[
  { t: <scene-4-start>, mode: FULLSCREEN },
  { t: <scene-5-start>, mode: BOTTOM },
].forEach(({ t, mode }) => {
  mainTl.to("#face-wrapper", { ...mode, duration: MODE_DUR, ease: "expo.inOut" }, t - 0.15);
});
```

A face that snaps modes instantly is the single most jarring frame. Always interpolate.

**BOTTOM scale caveat:** the default (0.5625) leaves dead space flanking most speakers. See `LESSONS.md` §2 for the corrected `{ x: -180, y: 1110, scale: 0.75 }`.

### Face grading (every short, no exceptions)

```css
#face-video { filter: contrast(1.08) saturate(1.08) brightness(0.97); }
```

Plus subtle 1.00 → 1.025 Ken Burns zoom over full duration (`ease: "none"`) and side-vignette `::after` pseudo-element.

### Seam treatment (required for bottom-half scenes)

Navy→transparent gradient band (60–100px) at y=960 + 2px accent scan line with soft glow. Draw AFTER face so it sits on top. Razor-sharp y=960 cuts = #2 tell for AI-edited content.

## Scene authoring

One scene = one sub-composition file. Scenes sit on same `data-track-index` back-to-back (no gaps).

- `data-duration` matches parent's slot exactly
- All GSAP anchors are LOCAL (0-based from scene start)
- Use `tl.set({}, {}, <data-duration>)` to pad timeline so GSAP `tl.duration()` matches

### Scene pacing rules (summary — full rationale in 10 rules below)

- **No dead frames.** Every 100ms has ≥1 animating element.
- **Payoff ≥ 1s hold.** Big reveal (stamp, number lock, punchline) ≥1s on screen.
- **Motion through full duration.** Secondary motion if entrances land early.
- **Vary eases.** ≥3 different eases per scene.
- **One jaw-dropper per 5s.** Typography slam, glitch, whip-pan, audio-sync slam.

## Captions (karaoke style)

- Montserrat 900, 46–58px (for 1080 width), 100% white base
- Active word: scale-1.08 pop + color change to accent (`#37bdf8` for AIS)
- Stroke via layered `text-shadow`, NEVER `-webkit-text-stroke` (renders inconsistently)
- Drop the rgba background pill — let the stroke hold readability
- For retimes, use `shift()` in `captions.html` to map transcript → edited-time (see `RETIME.md`)

See `references/captions.md` under `/hyperframes` for full karaoke implementation.

## Ambient background (never ship flat navy)

Minimum viable stack:

1. **Radial gradient base** (center lighter than edges by 15–20%)
2. **Animated noise/grain overlay** at 8–12% opacity
3. **4–8 drifting particle dots** or grid traces
4. **Subtle vignette**

For techy/control-room aesthetic, use 6-layer stack from `feedback_techy_background_layers.md`.

## Audio reactivity

- Headlines pulse 3–6% on beat. Backgrounds 10–30% on bass.
- Text kept subtle (3–6%) so captions stay readable
- Use SEEDED offline analyser (pre-compute the audio feature track). Do NOT use `AnalyserNode` in render path.

## Transitions

- **Rotate flavors.** No two consecutive the same. Six hard cuts in a row = #1 AI-editing tell.
- Face-mode transitions (`BOTTOM ↔ FULLSCREEN`) double as scene transitions when mode changes between scenes.
- For pure overlay: install from registry: `push-up`, `flash-through-white`, `sdf-iris`. `npx hyperframes catalog --type block`.

## The verification gate (mandatory — DO NOT ship without)

Lint passing ≠ design working. Never report done until frames extracted at word-exact timestamps and every PNG read.

### Step 1 — draft render

```bash
cd video-projects/<slug>
npx hyperframes lint
npx hyperframes render --quality draft --output renders/<slug>-vN-draft.mp4
```

### Step 2 — word-exact frame extraction

Pick 8–15 timestamps corresponding to SPOKEN WORDS where a specific visual should be on-screen. Not round numbers. Not mid-scene. The exact word.

```bash
mkdir -p renders/frames-vN
for pair in "<t>:<label>" "<t>:<label>" ...; do
  t="${pair%%:*}"; label="${pair##*:}"
  ffmpeg -y -ss "$t" -i renders/<slug>-vN-draft.mp4 \
    -frames:v 1 -q:v 2 "renders/frames-vN/t${t}-${label}.png"
done
```

### Step 3 — Read every PNG

Call `Read` on every PNG. For each: expected visual on-screen at expected moment, speaker not cropped, face mode correct, captions on-brand, no blank frames.

### Step 4 — fix + re-verify. Never ship broken.

### Step 5 — final render

```bash
npx hyperframes render --quality standard --output renders/<slug>-vN.mp4
```

Spot-check 3–4 frames from final render.

### Step 5.5 — promote to Content Hub (auto-link to project)

After Allen approves the final render, promote it to Content Hub so the Library + Projects Kanban sees it:

```bash
# Replace <PROJECT_ID> with the ideas.id this reel is for
# Replace <SCRIPT_ID> with the scripts.id (variant=reel) — optional but preferred
curl -s -X POST http://localhost:3000/api/library/promote \
  -H 'Content-Type: application/json' \
  -d "{
    \"local_path\": \"$(pwd)/renders/<slug>-vN.mp4\",
    \"project_id\": <PROJECT_ID>,
    \"script_id\": <SCRIPT_ID>,
    \"type\": \"reel\",
    \"variant_label\": \"vN\",
    \"render_meta\": { \"composition_id\": \"<slug>\", \"scene_count\": <N>, \"audio_duration\": <SEC> }
  }"
```

The endpoint:
- Uploads the MP4 to `r2://content-hub/ready/<project_id>/<asset_id>-<slug>.mp4`
- Inserts an `assets` row with `status='ready'`, `idea_id=<project_id>`, `script_id=<script_id>`
- Returns `{ asset_id, key, url }` — paste back to Allen so he can confirm

If `project_id` is unknown (one-off render), call without it and the asset lands as "Unlinked" in Library; pick a project later in the UI.

## The 10 rules (quality checklist — run BEFORE first draft)

1. **No dead frames.** Every 100ms animating.
2. **Scene payoff ≥ 1s hold.** Budget by reveal time.
3. **Face is a character.** Grade + Ken Burns + side vignette.
4. **No hard seams.** Feather y=960 with gradient + scan line.
5. **One jaw-dropper per 5s.** Slam/glitch/whip-pan/audio-sync.
6. **Audio reactivity non-negotiable.** 3–6% text, 10–30% bg.
7. **Rotate transition flavors.**
8. **Captions pop, don't politely label.** Stroke not pill.
9. **Motion through full scene duration.**
10. **Background is a layer, not a color.** Radial + noise + particles + vignette min.
11. **Slam/stamp lands AFTER target text fully visible.** Stamp `t` ≥ target-visible `t` + 0.10–0.25s.

## Project structure

```
video-projects/<slug>/
├── hyperframes.json
├── meta.json                    (id, name, 1080x1920, fps 30)
├── index.html                   (root, 4-layer scaffold)
├── compositions/
│   ├── ambient-bg.html
│   ├── seam-treatment.html
│   ├── captions.html
│   └── scene1..N-<label>.html
├── assets/
│   ├── <name>.mp4               (original)
│   ├── <name>-edit.mp4          (edited — comp uses this)
│   ├── transcript.json
│   └── brand assets
└── renders/
    ├── <slug>-v1-draft.mp4
    ├── frames-v1/
    └── <slug>-v1.mp4
```

## Speed target — 20 min per reel

Goal: render ONCE, use ffmpeg for everything after.

| Step | Time |
|---|---|
| Transcribe source audio | 2 min |
| Copy scene scaffold from prior reel | 5 min |
| **ONE** full Hyperframes render | ~8 min |
| ffmpeg composite (face + animation + sticker) | 30 sec |
| Frame-verify 4 key timestamps | 1 min |
| Final standard encode | 2–3 min |
| **Total** | **≈20 min** |

Rules:
- Render full composition ONCE. Never re-render for text tweaks.
- Every text/sticker iteration after → Chrome-headless PNG + ffmpeg overlay. See `FFMPEG-RECIPES.md`.
- Copy scenes from prior reels. Never author from scratch.

## Carousel handoff (after final render)

After Allen approves the final render, write `video-projects/<slug>/carousel_brief.json`:

```json
{
  "angle": "hook angle derived from reel's strongest claim",
  "key_points": ["sub-point 1", "sub-point 2", "sub-point 3"],
  "ccn_check": {
    "core": "what buyers get from this reel",
    "casual": "what followers would save/share",
    "new": "what a stranger learns in one read"
  }
}
```

This seeds `/carousel` so it starts with the reel's angle pre-filled rather than re-deriving from transcript.

## What NOT to do

- Animate `<video>` dimensions — freezes frames. Animate wrapper.
- `repeat: -1` on any timeline — breaks capture engine.
- `Math.random()` / `Date.now()` — breaks determinism. Seeded PRNG if needed.
- `<br>` inside captions — natural wrapping + `<br>` = extra breaks.
- Skip frame verification gate.
- Author in original-time if audio is edited.
- Leave `background: #07121c` flat.
- Hard-cut between scenes.
- Politely label with captions.
- Let face sit still.

## Reference compositions

- `video-projects/may-shorts-19/` — canonical short-form example (18.84s, 7 scenes, face-mode choreography, karaoke captions)
- `video-projects/may-shorts-18/` — secondary reference with 4 v1→v2 fixes baked in (see `LESSONS.md`)
- `projects/personal/videos/reel-3/` — hook-sticker + spy-avatar + ffmpeg-composite pattern (see `FFMPEG-RECIPES.md` Recipe 2)

## Related skills (invoke in addition)

- `/hyperframes` — framework rules (always first)
- `/hyperframes-cli` — CLI commands
- `/gsap` — animation library reference
- `/hyperframes-registry` — installing transition blocks
- `/seedance-loop-prompt` — AI-generated looping background video

## Memory pointers (read only if situation matches)

- `feedback_short_form_principles.md` — 10 rules rationale
- `feedback_visual_verification.md` — verification gate
- `feedback_hook_sticker_style.md` — hook sticker spec (covered in `HOOK-STICKER.md`)
- `feedback_captions_style.md` — karaoke captions spec
- `feedback_overlay_png_chrome_headless.md` — Chrome-headless + ffmpeg fast path (covered in `FFMPEG-RECIPES.md`)
- `project_ais_brand_specs.md` — AIS-branded reels (hex, fonts, logo glow)
