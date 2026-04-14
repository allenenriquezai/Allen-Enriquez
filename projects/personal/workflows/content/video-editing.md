# Video Editing SOP

Edit raw footage into Hormozi-style videos. Reels (30-60s, 9:16) and YouTube (7-12min, 16:9).

## Style

Primary: Alex Hormozi -- raw, educational, value-first. Borrow punch-in zooms and clean sound design from Iman Gadzhi. NOT lifestyle/luxury content.

## Setup

1. Read style guide: `projects/personal/reference/hormozi-style-guide.md`
2. Check deps: `python3 tools/edit_video.py check-deps`
3. If SFX missing: `python3 tools/edit_video.py generate-sfx`

## Workflow

Present options at each step. Never auto-decide without showing Allen.

### Step 1 -- Transcribe

```bash
python3 tools/edit_video.py edit --input "<path>" --type <reel|youtube> --captions off --no-zoom 2>&1 | head -30
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
python3 tools/edit_video.py edit \
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
