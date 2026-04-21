# Short-Form Video — Lessons from May Shorts 18 (v1 → v2)

**Load this file when:** first build of a new reel, or when a reel "feels rigid / bland / off."

Distilled from the 4 concrete problems the may-shorts-18 v1 render had and what fixed them in v2. Apply these on every new short.

## 1. Slam/stamp timing — reveal logic beats word-sync

A SLAM/STAMP overlay (KILLED, DEAD, STOP, etc.) lands AFTER its target text is fully visible, **not** during the spoken word. In may-shorts-18 v1 scene 1, CLAUDE and CHATGPT were pitched as opponents — KILLED fired at local 0.46s while CHATGPT didn't appear until 0.66s, so viewers saw "Claude … KILLED" with no visible target. The joke collapsed.

**Rule:** `stamp_t ≥ target-text-visible_t + 0.10–0.25s`. The "visible" timestamp is the END of the target's entrance animation, not its start. Word-sync is a guideline; visual reveal order is the constraint.

## 2. BOTTOM face-mode scale — don't ship the default

Default `BOTTOM = { x: 0, y: 1136, scale: 0.5625 }` (exact horizontal fit for a 1920×1080 source) leaves empty studio background flanking the speaker if they occupy <70% of the source frame. This is the default in may-shorts-19 and was copied into may-shorts-18 v1 — both videos had visible dead space left and right of the speaker in every BOTTOM scene.

**Rule:** prefer `BOTTOM = { x: -180, y: 1110, scale: 0.75 }` — crops 180px each side, bottom-anchors to y=1920. Preview ONE frame of BOTTOM mode against the actual source video before committing the constant. If the source speaker is tight-framed already, scale 0.65 may be enough; if the source is wide studio framing, push to scale 0.80 and re-tune x.

Always keep HIDDEN's `x`, `y`, `scale` identical to BOTTOM — they only differ in `opacity` — so the opacity-fade scenes don't drift geometrically mid-fade.

## 3. Face-mode transitions — three things at once, not one

When the face changes mode between adjacent scenes, a bare 0.15s pre-roll + 0.32s duration `expo.inOut` on just the face wrapper reads as rigid — the outgoing scene's panels are still fully opaque behind the morphing face, so the eye sees two things fighting instead of a crossfade.

**Rule:** for any "hero" scene-to-scene face-mode change (especially BOTTOM ↔ FULLSCREEN), do all three:
1. Extend that specific transition's duration to 0.45–0.55s (not the default 0.32s)
2. Start it 0.25–0.30s before the new scene's `data-start` (not the default 0.15s)
3. Fade + blur the outgoing scene's panel wrapper to `opacity: 0, filter: blur(6px)` over 0.20–0.25s, starting 0.25s before scene end

Implementation-wise, promote the face-mode transition array to per-entry `dur` so one transition can be longer than the others:
```js
[ { t: 2.06, mode: FULLSCREEN, dur: 0.50 }, { t: 3.71, mode: HIDDEN, dur: 0.32 }, ... ]
  .forEach(({ t, mode, dur }) => mainTl.to("#face-wrapper", { ...mode, duration: dur, ease: "expo.inOut" }, t));
```

Three simultaneous changes = "a real editor edited this." Any one alone = rigid.

## 4. Data-feel scenes beat decoration scenes mid-video

For scenes 3–5 of a 15–20s short (the "middle grind" where attention drops the hardest), lean on visuals that read as information — bar races, stat grids with counting numbers, heatmaps, sparklines, flowcharts, dashboard chrome with telemetry ticking, pain-point grids that flash red in sequence. may-shorts-18 v1 scene 4 was a radar-rings + terminal-chip + sparks combo — functional but decorative, and Nate called it "bland." v2 replaced it with a 3×3 pain-point grid lighting up red-orange in sequence + a sparkline stroke-drawing with a YOU-ARE-HERE marker + the payoff slam — same time budget, much higher engagement.

**Rule:** pure typography-plus-icon scenes feel like slides. Data-feel scenes feel like evidence. When a middle scene feels bland, replace the decoration with something that reads as *information*: a small number ticking up, a bar filling, a chart stroking in, a grid flashing in sequence.
