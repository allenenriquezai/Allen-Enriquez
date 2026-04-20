---
name: scene-animation
description: Build and preview a single scene's motion graphic animation in isolation BEFORE the full reel is assembled. Use when Allen says "animate a scene", "preview animation", "scene animation", "build the animation first", "make an animation", "let me see the animation", or before running `/short-form-video` on any new reel. Locks scene motion in browser preview (localhost:3002?comp=<id>) so animation tweaks cost seconds, not an 8-min full re-render.
---

# Scene Animation (Hyperframes)

Build scene motion graphics in isolation, scrub-approve in browser, lock. THEN hand off to `/short-form-video` to layer face + audio + captions on top.

**Why:** Full Hyperframes render on Mac = ~8 min (screenshot-capture mode). Every animation tweak re-renders face + audio + captions too — wasteful. This skill uses `npx hyperframes preview` hot reload (localhost:3002) so animation iteration = seconds, not minutes. Full reel renders ONCE after animations locked.

**Always invoke `/hyperframes` first.** Framework rules (`data-*` attributes, `window.__timelines`, determinism) apply regardless. `/gsap` for animation API.

## When this skill fires

- "Animate scene N", "build scene animation", "preview animation"
- Before `/short-form-video` on a new reel — this skill runs FIRST
- "Let me see the animation before we build the full reel"
- Iterating on motion of an existing scene (edit + re-preview, no full render)

## The flow

```
1. /scene-animation  ← you are here
   ├─ Read beats/script (beats.md)
   ├─ Scaffold compositions/sceneN-<label>.html (empty shells)
   ├─ Build GSAP timeline for each scene
   ├─ npx hyperframes preview → localhost:3002?comp=<scene-id>
   ├─ Allen scrubs, tweaks, locks each scene
   └─ HANDOFF when all scenes approved
2. /short-form-video
   ├─ Pick up locked scenes
   ├─ Layer face video, audio, captions
   └─ ONE full render
```

## Step 1 — Read the beats

Every reel has a beats file describing scene content + timing. Usually:
- `projects/personal/videos/<reel>/beats.md`
- Or BRIEF.md / STORYBOARD.md from `/make-a-video` Gate 4

Extract per scene:
- `scene-id` (kebab-case: `scene1-hook`, `scene2-inbox`, etc.)
- `data-start` (in edited-time, 0-based)
- `data-duration` (seconds, to 2 decimals)
- concept / visuals / payoff moment

If no beats file exists, ask Allen for the scene list before scaffolding.

## Step 2 — Scaffold scene HTML

One file per scene under `compositions/`. Template:

```html
<template id="sceneN-<label>-template">
  <div data-composition-id="sceneN-<label>"
       data-start="0"
       data-width="1080"
       data-height="1920"
       data-duration="<SECONDS>">
    <style>
      [data-composition-id="sceneN-<label>"] {
        position: absolute; inset: 0;
        background: #05080F;
        color: #fff;
        font-family: "Montserrat", sans-serif;
      }
      /* scoped styles here */
    </style>

    <!-- DOM -->
    <div class="hero">...</div>

    <script>
      (function(){
        const SLOT_DURATION = <SECONDS>;
        const tl = gsap.timeline({ paused: true });

        // tweens — LOCAL offsets (0-based from scene start)
        // tl.from(".hero", { y: 60, opacity: 0, duration: 0.4, ease: "power3.out" }, 0.1);

        tl.to({}, { duration: SLOT_DURATION }, 0); // anchor — Motion Law 11
        window.__timelines = window.__timelines || {};
        window.__timelines["sceneN-<label>"] = tl;
      })();
    </script>
  </div>
</template>
```

**Critical:**
- `data-duration` matches the slot from beats.md exactly
- Anchor tween at end — `tl.to({}, { duration: SLOT_DURATION }, 0)` — required for frame accuracy (Motion Law 11)
- All GSAP offsets LOCAL (0-based from scene start), never global time
- Scope styles via `[data-composition-id="..."]` — prevents bleeding into other scenes
- No `Math.random()`, no `Date.now()`, no render-time `fetch()` (determinism)

## Step 3 — Wire scene into index.html (preview-only config)

Minimal `index.html` at project root for isolated preview. Face/audio/captions tracks stay **commented out** — they don't exist yet:

```html
<!DOCTYPE html>
<html>
<head>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>html,body{margin:0;background:#05080F;}</style>
</head>
<body>
  <div id="main" data-composition-id="main"
       data-start="0" data-width="1080" data-height="1920"
       data-duration="<TOTAL_REEL_DURATION>">

    <!-- Track 1: scenes (back-to-back, no gaps) -->
    <div data-composition-src="compositions/scene1-hook.html"
         data-track-index="1"
         data-start="0"></div>
    <div data-composition-src="compositions/scene2-inbox.html"
         data-track-index="1"
         data-start="<scene1_end>"></div>
    <!-- ... -->

    <!-- LAYERED IN /short-form-video — keep commented here -->
    <!-- <video id="face-video" data-track-index="0" ... /> -->
    <!-- <audio data-track-index="0" ... /> -->
    <!-- <div data-composition-src="compositions/captions.html" data-track-index="20"></div> -->
  </div>
</body>
</html>
```

## Step 4 — Launch preview, iterate per scene

```bash
cd projects/personal/videos/<reel>
npx hyperframes lint      # catch composition errors first
npx hyperframes preview   # serves localhost:3002 with hot reload
```

For each scene, hand Allen the per-composition URL:
```
http://localhost:3002/?comp=scene1-hook
http://localhost:3002/?comp=scene2-inbox
...
```

Per-scene URL scrubs the single composition in isolation. Allen scrubs, plays, notes what needs tweaking. You edit the scene file, hot reload fires, Allen re-scrubs. Loop until scene is locked.

**Ask explicitly: "Scene N locked?"** Don't assume approval. Silence ≠ yes.

## Step 5 — Lock check before handoff

Before handing off to `/short-form-video`, confirm:

- [ ] Every scene in beats.md has a matching `compositions/sceneN-<label>.html`
- [ ] Every scene's `data-duration` matches beats.md exactly
- [ ] Every scene's GSAP timeline ends with anchor tween at `SLOT_DURATION`
- [ ] Every scene passes `npx hyperframes lint`
- [ ] Allen has scrub-approved each scene at `localhost:3002?comp=<id>`
- [ ] Scene back-to-back math adds up — sum of `data-duration` = total reel runtime from beats

Then: "Scenes locked. Running `/short-form-video` to layer face + audio + captions."

## Scene pacing rules (apply during authoring, not after)

Inherited from short-form 10 rules — enforce during preview:

1. **No dead frames.** Every 100ms has ≥1 animating element. Offset first entrance 0.1–0.3s, not t=0.
2. **Payoff ≥ 1s hold.** Big reveal (stamp/number/punchline) must sit ≥1s, ideally 1.5s.
3. **Motion through full duration.** If entrance anims land by local 2s on a 4s scene, add secondary motion: underline sweeps, checkmark pops, ambient drift, oscillating glows.
4. **Vary eases.** ≥3 different eases per scene.
5. **Slam/stamp AFTER target visible.** `stamp_t ≥ target-visible_t + 0.10–0.25s`. Reveal logic > word-sync.
6. **One jaw-dropper per 5s.** Typography slam, glitch, whip-pan.

## Brand tokens (use these, not defaults)

From `project_brand_color.md` + `project_brand_visual_system.md`:

- Primary: `#02B3E9` (cyan — highlights, glows, accents)
- Base: `#05080F` (deep navy — backgrounds)
- Confirmation: `#22c55e` (green — PAID stamps)
- Alert: `#ff4757` (red — OVERDUE tags, warnings)
- Display: Montserrat 900 (headings, numerals — Google Fonts)
- Mono: Roboto Mono 400/500/700 (chrome, telemetry — Google Fonts)

## Boundaries — what this skill does NOT do

- **No face video.** Talking head gets layered by `/short-form-video`.
- **No audio.** TTS / narration / music = `/short-form-video`.
- **No captions.** Karaoke captions = `/short-form-video`.
- **No ambient-bg or seam-treatment full scaffold.** That's 4-layer scaffold territory = `/short-form-video`.
- **No MP4 render.** If you're rendering MP4 you're past this skill's scope. Hand off.

This skill = scenes only. Nothing else.

## Retime behaviour

If Allen edits the audio AFTER scenes are locked (new cut removes 2s somewhere), scenes straddling the cut need both parent `data-start` and internal GSAP offsets shifted. Re-preview affected scenes. Don't run full reel render until re-confirmed.

See `/short-form-video` retime protocol for the full mechanics — this skill only handles the scene-internal part.

## Related skills

- `/hyperframes` — framework rules (always first)
- `/gsap` — GSAP API reference for timelines + eases
- `/hyperframes-cli` — `lint`, `preview` commands
- `/hyperframes-registry` — catalog blocks for scene elements
- `/short-form-video` — picks up here after scenes locked (face + audio + captions)
- `/make-a-video` — upstream interview + brief; calls this skill at Gate 5.5

## Memory pointers

- `feedback_reel_style.md` — caption/hook/face preferences
- `feedback_hook_sticker_style.md` — hook sticker spec (applied in `/short-form-video`, not here)
- `feedback_captions_style.md` — karaoke spec (applied in `/short-form-video`, not here)
- `project_brand_color.md` — `#02B3E9` primary
- `project_brand_visual_system.md` — full visual token system
- `project_hyperframes_video_stack.md` — why this stack, why preview-first
- `project_reel_speed_target.md` — 20-min reel budget, single-render pipeline
