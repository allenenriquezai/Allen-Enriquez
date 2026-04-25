---
name: carousel
description: Turn a posted reel into a Hormozi-style 1080×1350 carousel. Reads only transcript.json + meta.json from the reel folder. CCN framework inline. Triggers on "carousel from [reel]", "make a carousel", "turn this reel into slides".
---

# Carousel Skill

Turns a posted reel into a static Hormozi-style carousel (1080×1350, white bg, bold black, brand blue accent).

## Triggers

- "Make a carousel from [reel-id/name]"
- "Turn this reel into a carousel / slides"
- "Create a carousel" — ask which reel if not specified

## Step 0 — Load (2 files only)

```
projects/personal/content/reels/<reel-id>/assets/transcript.json
projects/personal/content/reels/<reel-id>/meta.json
```

Do NOT load CONTEXT.md, workflows, or any other file.

## Step 1 — CCN filter (Sam Gaudet framework)

Every slide must serve all 3 audiences simultaneously:

- **Core** (buyers): sees proof, framework, or credibility signal
- **Casual** (followers): saves or shares — useful or surprising
- **New** (strangers): understands the point in one read, zero prior context

Test each content slide: would a cold stranger stopping their scroll get this without having seen the reel? If no, rewrite.

## Step 2 — Copy

**Structure:**
| Slide | Format | Rules |
|---|---|---|
| 1 (title) | `HOOK \|\| One-line subhook` | Hook = biggest claim, exact transcript words, max 8 words |
| 2–N-1 (content) | `LABEL \|\| Body` | Label = 1–3 word keyword; body = one idea, max 15 words |
| Last (CTA) | Single action, no `\|\|` | Mirror reel's CTA where possible |

**Slide count:** 5 for simple reels (1 main + 3 sub-points), 7 for rich reels (4–5 sub-points). Max 8.

**Rules:** Use exact transcript language. One idea per slide. No filler. Slide 2 = strongest sub-point.

## Step 3 — Generate

Save copy to `.tmp/<reel-id>-carousel-copy.txt` in `--- Slide N ---` format, then run:

```bash
python3 tools/personal/generate_carousel.py \
  --topic "<hook-text>" \
  --slides <N> \
  --handle "@allenenriquezz" \
  --copy-file .tmp/<reel-id>-carousel-copy.txt
```

Output: `projects/personal/content/carousels/<slug>/`

## Step 4 — Review

Read all slide PNGs. Flag:
- Slide 1 hook cramped (too many wrapped lines)
- Any content slide with >4 body lines and no `||` split → rewrite as `LABEL || short body`
- Profile header present on slides 1 and N

Show Allen the copy list and slide count. Ask to approve before calling done.

## carousel_brief.json spec

Written to `projects/personal/content/reels/<reel-id>/carousel_brief.json` after every run:

```json
{
  "angle": "carousel hook angle",
  "key_points": ["point 1", "point 2", "point 3"],
  "ccn_check": {
    "core": "what buyers get",
    "casual": "what followers save/share",
    "new": "what strangers learn in 30s"
  }
}
```

## Profile Header SOP

Slides 1 and last always show the profile header. **Do not change these values without Allen's explicit approval.**

**Layout (left to right):**
- Circular photo → Name (bold) → Handle (below name)

**Photo specs:**
- Source: `projects/personal/brand/profile.png`
- Diameter: 160px with 5px border
- Position: x=100 (PADDING_X), y=280 (PADDING_TOP + 160)
- Crop: `crop_h = int(h * 0.74)`, `side = min(w, crop_h)`, `left = (w - side) // 2`, `top = h - side`
  - This zooms into the bottom 74% of the portrait, pushing the face near the top of the circle with a small gap

**Name specs:**
- Font: Helvetica Bold, 64px
- Color: `(15, 15, 15)` (near-black)
- Position: x = photo_x + photo_size + 28 = 288, y = photo_y + 36 (vertically centered with photo)

**Handle specs:**
- Font: Helvetica Regular, 40px
- Color: `(80, 80, 80)` (dark gray)
- Position: y = name_y + 66 (directly below name)
- Text: `@allenenriquezz`

If photo is missing from slides, check that `projects/personal/brand/profile.png` exists.

## What NOT to do

- Load CONTEXT.md or any workflow files
- Paraphrase transcript — use exact words
- Auto-approve copy (always show Allen first)
- Exceed 8 slides
