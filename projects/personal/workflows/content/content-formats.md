# Content Formats — Production Rules

The content agent reads this to know format-specific rules for each content type.

---

## Reel (Short-form video)

**Platforms:** Instagram, Facebook, TikTok, YouTube Shorts
**Length:** 30-60 seconds
**Word limit:** 150 words (script)
**Orientation:** Vertical (9:16)
**Structure:** Hook → Problem → Solution → CTA

### Script format
```
[HOOK + PROOF] (0-5 sec)
<bold claim with built-in credibility — one sentence>
Example: "I manage 83 deals by myself. Here's how."

[PROMISE] (5-10 sec)
<what they'll get from this reel>

[CONTENT] (10-45 sec)
<deliver the value — 2-3 steps max, show don't tell>
<mini-tutorial: quick screen recording with text overlays>

[CTA] (45-60 sec)
<full tutorial on YouTube / follow for more>

---
CAPTION: <short text for post caption, 1-2 sentences + hashtags>
TEXT OVERLAYS: <key words/numbers to show on screen>
```

### Rules
- One idea per reel. Never two.
- Same reel posts to all 4 platforms.
- Captions must work without audio (many watch on mute).
- Text overlays: max 5 words per overlay, 3-4 overlays per reel.
- No intro. No "hey guys". Start with the hook immediately.
- Reels are mini-tutorials of the day's YouTube — compressed, fast, edited.
- Batch film: do 4-5 reels in one session, change shirt between takes.

---

## YouTube (Long-form video)

**Platform:** YouTube
**Length:** 7-12 minutes
**Word limit:** 1500 words (script)
**Orientation:** Horizontal (16:9)
**Structure:** Hook → Proof → Promise → Plan → Content (retain) → Proof Stack → Reward → CTA

### Script format
```
--- HOOK PHASE ---

[HOOK] (0-5 sec)
<pattern interrupt — bold claim, surprising number, or pain point>

[PROOF] (5-20 sec)
<your credibility — specific result, not a title or bio>

[PROMISE] (20-40 sec)
<what they'll walk away with — specific and measurable>

[PLAN] (40-60 sec)
<how the video is structured — "3 parts" or "5 steps", set time expectations>

--- RETAIN PHASE ---

[CONTENT] (60 sec - 7 min)
Chapter 1: <one idea>
  - Teach: <explain simply>
  - Show: <screen share or demo>
  - Result: <what this achieved — specific number>
Chapter 2: <one idea>
  - Teach / Show / Result
Chapter 3: <one idea>
  - Teach / Show / Result

[PROOF STACK] (7-8 min)
<stack all results together — before/after comparison, total numbers>

--- REWARD PHASE ---

[REWARD] (8-9 min)
<the big takeaway — one sentence they'll remember and repeat>

[CTA] (9-10 min)
<subscribe + "Watch this next" with specific video mention>

---
TITLE: <under 60 chars, curiosity-driven>
DESCRIPTION: <3 lines — what they'll learn, who it's for, subscribe link>
CHAPTERS:
  0:00 — <hook>
  0:05 — <proof + promise>
  0:40 — <plan>
  1:00 — <chapter 1>
  ...
THUMBNAIL IDEA: <visual concept for thumbnail>
```

### Rules
- One idea expanded. Deep, not wide.
- Every chapter needs: teach, show, result.
- Proof is woven INTO the content, then stacked at the end.
- Chapter markers required for every section.
- Thumbnail + title decide if someone clicks. Script decides if they stay.
- First 60 seconds must hook, prove credibility, promise value, and set expectations.
- Record screen shares separately — insert during editing.

---

## Facebook Group Post

**Platform:** Facebook groups
**Length:** 50-100 words
**Structure:** Value → Insight → Question

### Format
```
<value statement or result — 1-2 sentences>

<brief explanation or tip — 1-2 sentences>

<engagement question>
```

### Rules
- No links. No selling. No pitching. Pure value.
- Answer a question someone in the group might have.
- End with a question that invites replies.
- If someone asks "how?" in comments — DM them. Don't pitch publicly.
- Max 2 posts per group per week. Don't be spammy.
- Read the group rules before posting. Follow them.

---

## LinkedIn Post

**Platform:** LinkedIn
**Length:** Under 200 words
**Structure:** Hook → Insight → Example → Question

Follows existing `content-calendar.md` SOP. No changes.

---

## Carousel (Static image set)

**Platforms:** Instagram, Facebook, LinkedIn
**Slides:** 5-10 (7 is sweet spot)
**Dimensions:** 1080x1080px (square)
**Orientation:** Square (1:1)
**Structure:** Hook slide → Value slides (1 idea each) → CTA slide

### Styles
- **Dark mode** (Hormozi style): Black background, white bold text. High contrast. Authoritative.
- **Light mode** (Nate Herk style): White background, black bold text. Clean. Approachable.

### Slide rules
- **Slide 1 (Hook):** Topic as bold claim. All caps. Handle at bottom. Must stop the scroll.
- **Slides 2-N-1 (Value):** One idea per slide. Max 15 words. Bold text, centered. Slide counter at top.
- **Slide N (CTA):** Call to action — save, share, follow. Handle at bottom.
- Swipe indicator dots at bottom of every slide.
- No images, no gradients, no icons. Text only. Let the words do the work.

### Copy rules (Hormozi voice)
- 3rd grade reading level. If a kid can't read it, rewrite it.
- Max 10 words per sentence.
- No jargon. No filler. Bold claims backed by simple logic.
- Each slide must make sense on its own (people screenshot individual slides).

### Production
```
python3 tools/personal/generate_carousel.py --topic "Your hook here" --slides 7 --style dark --handle "@allenenriquez"
```
- Generates PNGs to `.tmp/carousels/<topic-slug>/`
- Also outputs `copy.txt` — edit this, then re-run with `--copy-file` to regenerate with custom text.
- Use `--style light` for Nate Herk style.

---

## Cross-Platform Repurposing

One idea can become multiple pieces:

| Source | Repurpose to |
|---|---|
| YouTube video | 2-3 reels (clip key moments), 1 LinkedIn post, 1 FB group post |
| Reel | LinkedIn post (text version), FB group post |
| FB group post | Reel (film the answer), LinkedIn post |

### Repurposing rules
- Change the hook for each platform. Same hook = same scroll-past.
- Reels from YouTube: pick the single best 30-60 second segment.
- Text posts from video: don't transcribe — rewrite for reading.
- Track which ideas have been repurposed in the content tracker.

---

## Editing Rules (Hormozi Style)

AI-assisted editing via Hyperframes stack (HTML + GSAP + Puppeteer). See `project_hyperframes_video_stack` memory.

### Reel Editing Rules (Hormozi Style)

**Skill:** `/short-form-video` — vertical 9:16 (TikTok/Reels/Shorts)
**Kit:** `projects/personal/reference/hyperframes-student-kit/`

**Silence removal:**
- Cut all pauses > 0.4s, filler words, breaths. Zero dead air.
- auto-editor with -30dB threshold, 0.4s minimum duration.

**Captions (always on for reels):**
- Font: Anton (Google Fonts) or Montserrat Bold. Uppercase.
- White text, yellow stroke/highlight on keywords.
- Word-by-word highlighting — active word changes color.
- Max 15 chars per line, 2 lines max, 4-6 words per display.
- Centered in lower third. Min 2s display time. Pop-in animation.

**Punch-in zoom ("Hormozi Pulse"):**
- Slow zoom 100% → 120% over 3-5s on key points.
- Hard cut back to 100% to reset. Use on bold claims and numbers.

**Transitions:** Hard cuts between sentences (default). White flash (0.2-0.3s) between major sections.

**SFX:** Whoosh on section transitions. Pop/click on text appearances. Background music at -20dB.

**Color grading:** Saturation 1.3x, contrast 1.1x, slight brightness boost. Clean and punchy, not cinematic.

**Pacing:** Aggressive cuts. 1 idea per 10 seconds. No pauses. No "umm".

### YouTube Editing Rules (Hormozi Style)

**Skill:** `/make-a-video` — long-form 16:9 via Hyperframes
**Kit:** `projects/personal/reference/hyperframes-student-kit/`

**Silence removal:**
- Same threshold as reels but preserve natural breathing room between sections.
- Cut filler words and long pauses, keep brief pauses for emphasis.

**Captions:** Optional for YouTube (most watch with audio). Enable for accessibility.

**Punch-in zoom:**
- Same technique as reels. Apply on key points, bold claims, numbers.
- 3-5 zoom sections per video. Don't overuse.

**B-roll — Doodle explainers (Hormozi book style):**
- Simple whiteboard-style concept diagrams — stick figures, hand-drawn boxes, arrows, minimal color.
- Style reference: $100M Offers book illustrations.
- Generated via Excalidraw diagram skill. Agent identifies "concept explanation" moments in transcript → generates matching doodle → inserts as overlay.
- These replace stock footage — every B-roll insert should TEACH, not decorate.
- Also supports: screenshots, screen recordings at marked timestamps.
- Insert B-roll every 15-30s to break up talking head.

**Text overlays (long-form):**
- Numbered frameworks on screen ("Step 1", "Step 2").
- Key concept reinforcement as bold text overlay.
- Chapter markers via text overlays + jump cuts.

**Transitions:** Hard cuts default. White flash between major sections. Crossfade for chapter breaks.

**SFX:** Whoosh on transitions. Pop on text. Background music at -20dB, rises during B-roll.

**Color grading:** Same as reels — saturation 1.3x, contrast 1.1x, brightness boost.

**Pacing:** Medium. 1 idea per 60-90s. Breathe between sections. Let ideas land.

**Chapter markers:** Required for every section. Add to YouTube description.
