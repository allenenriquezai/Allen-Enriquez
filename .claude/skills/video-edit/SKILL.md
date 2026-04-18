---
name: video-edit
description: Edit video for personal brand content. Triggers on "edit video", "edit the reel", "cut the footage", "video editing", "edit my video", or /video-edit.
---

Video editing for Allen's personal brand. Reels (30-60s, 9:16) and YouTube (7-12min, 16:9).

## Inputs needed (ask upfront if missing)
1. **Video file path** — raw footage location
2. **Type** — reel or youtube
3. **Goal** — what's the video about, key message

## How to run

1. Read `projects/personal/CONTEXT.md` for brand rules
2. Read `projects/personal/workflows/content/video-editing.md` and follow it exactly
3. Read `projects/personal/reference/hormozi-style-guide.md` for style reference

## Quick Style Reference

**Captions (Hormozi)**
- 90pt+ SFPro Bold, white text
- Active word: yellow (#FFD500) rounded box behind it, black text on top
- 3px black drop shadow on other words
- Position: center screen, base_y = H - 420 - text_height
- Never blue highlights, never just-colored-text

**Layout (1080x1920 reel)**
- Title slam: center (~y=910)
- Illustrations: y=600-1100 zone
- Captions: ~y=1300-1500
- Everything compressed into center 40% of screen

**Face Rules**
- Face ON for hook (first 5-6s) + CTA (last ~13s)
- Illustrations replace face only during teaching sections
- Third-party faces: GaussianBlur radius 20

**Brand**
- Accent: #02B3E9 (blue) for titles, UI, glow effects
- Caption highlight: #FFD500 (yellow box)
- "FREE" always capitalized

**Pipeline**
- Reel renderer: `projects/personal/.tmp/video_test/full_video_v4.py` (illustrations, timing, captions)
- Reel compositor: `projects/personal/.tmp/video_test/full_video_v5.py` (face + overlays + captions)
- General editor: `tools/edit_video.py`
- Pillow renders frames, FFmpeg stitches + audio. Zero cost, fully local.

## Rules
- NEVER auto-edit without showing Allen the plan first
- NEVER skip transcript review step
- Present options at each step — never auto-decide
- Every B-roll insert must TEACH, not decorate
- If a step fails, show error and suggest fix. Don't retry silently.
- Reels: aggressive cuts, punchiness. YouTube: preserve breathing room.
