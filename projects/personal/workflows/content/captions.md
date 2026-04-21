# Caption Generation — SOP

Write platform-specific captions + hashtags for every reel/post. Hybrid method: viral reference modeling + platform meta rules + voice filter.

## Method (run in this order)

### 1. Reference Modeling (per post)
For every new script, find 2-3 viral posts with the SAME angle.

- Search platform (IG/TikTok/YT) for the hook topic: "AI agents vs ChatGPT", "AI for business owners", etc.
- Filter: 100k+ views OR engagement rate >5% OR posted in last 90 days.
- Verify actually viral. Ignore posts from mega-accounts where virality is guaranteed regardless of caption.
- Pull their caption. Note:
  - Hook structure (first line)
  - Line breaks / paragraph rhythm
  - CTA placement + style
  - Hashtag count + mix (broad vs niche)
  - Emoji usage (yes/no, how many, where)

### 2. Platform Meta Rules (static — don't re-research)

| Platform | Tag count | Hook rule | Notes |
|---|---|---|---|
| Instagram Reels | 5 max (Dec 2025 cap) | Hook line 1, break for "more" | 1-2 broad + 3 niche. No external links. |
| Facebook Reels | Same as IG | Same as IG | Cross-post identical from IG. |
| TikTok | 3-5 | Keyword-rich caption (TikTok search = huge) | #fyp is placebo. Keep under 300 chars. |
| YouTube Shorts | 3 | Title-style caption | #Shorts + niche + trend. |
| LinkedIn | 3 max | Hook in first 49 chars (pre "see more") | NO external links (algo penalty). Reply to every comment in first 90 min (determines 70% of reach). |

### 3. Voice Filter
Rewrite viral structure in Allen's voice. Never copy words verbatim.
- 3rd grade reading level
- Max 10 words per sentence
- No banned words (see `CONTEXT.md`)
- CTA: "Comment [WORD] — I'll help you set one up for free"

### 4. Output
Present captions in this order per script:
1. IG + FB (same)
2. TikTok
3. YouTube Shorts
4. LinkedIn

Include posting notes: engagement window, pin-comment strategy, first-90-min rule.

## Why hybrid beats either alone

- **Pure meta research** → generic captions that follow rules but don't hook.
- **Pure copy-modeling** → might ignore platform rules (e.g. LinkedIn link = dead post).
- **Hybrid** → viral framework + platform-correct + Allen's voice.

## Rule: Never transcribe video script into caption

Caption ≠ script. Caption's job: stop the scroll, give enough value to tap, drive the CTA. The video does the teaching.

## Rule: Verify virality before modeling

A post with 2k views is not a model. Filter ruthlessly:
- 100k+ views (short-form)
- 5%+ engagement rate (LinkedIn/text posts)
- Posted in last 90 days (algo changes fast)

## Rule: Model the framework, not the words

If viral post opens with "POV: you just realized..." — steal the POV hook pattern, not the exact phrasing. Algos flag near-duplicate captions.

---

# In-Video Karaoke Caption Spec

This is the locked visual spec for on-screen karaoke captions (the word-by-word text burned into reel video), separate from post-caption copy above.

- **Font:** Montserrat 900, UPPERCASE, ~68px base for 1080-wide frame
- **Stroke:** layered `text-shadow` — 4-way offsets `-3/3/3/3 0 #000` + diagonal `-4/0/4/0` + soft `0 6px 16px rgba(0,0,0,0.6)`. NEVER `-webkit-text-stroke` (renders inconsistently in Chromium capture).
- **Active word:** scale 1.16 pop (back.out(3), 0.08s in / 0.12s out) + color cross-fade to brand blue `#02B3E9` via stacked `.w-active` span. Never tween `color` directly.
- **Background:** none. No pill, no rgba backer. Stroke carries readability.
- **Position:** `bottom: 280px` for center-bottom placement in 1920-tall portrait.
- **Timing:** word-synced from whisper transcript; 6–7 word segments; segment visible until next segment's first word (hard cut).

Reference working files: `projects/personal/videos/reel-2/compositions/captions.html` and `reel-3/compositions/captions.html`. Both use identical CSS + GSAP karaoke pattern.
