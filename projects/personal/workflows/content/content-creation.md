# Content Creation — Writing SOP

Write reel scripts, YouTube scripts, FB group posts, LinkedIn posts. All content follows Hormozi style.

## References

- Style guide: `projects/personal/reference/hormozi-style-guide.md`
- Case study: `projects/personal/case-studies/eps-quote-automation.md`
- Format specs: below

## Tools

| Content Type | Command |
|---|---|
| Reel | `python3 tools/generate_content.py --type reel --topic "<topic>"` |
| YouTube | `python3 tools/generate_content.py --type youtube --topic "<topic>"` |
| FB group post | `python3 tools/generate_content.py --type fb-group-post --topic "<topic>"` |
| LinkedIn | `python3 tools/generate_content.py --type linkedin --topic "<topic>"` |
| Batch day | `python3 tools/generate_content.py --batch-day <N>` |

Drafts output to `.tmp/content_drafts.json`.

---

## Format: Reel (30-60 sec)

**Platforms:** IG, FB, TikTok, YT Shorts
**Word limit:** 150 words
**Structure:**

```
[HOOK + PROOF] (0-5 sec)
<bold claim with built-in credibility>
Example: "I manage 83 deals by myself. Here's how."

[PROMISE] (5-10 sec)
<what they'll get from this reel>

[CONTENT] (10-45 sec)
<2-3 steps max, show don't tell, mini-tutorial>

[CTA] (45-60 sec)
<full tutorial on YouTube / follow for more>

---
CAPTION: <1-2 sentences + hashtags>
TEXT OVERLAYS: <key words/numbers, max 5 words each, 3-4 per reel>
```

**Rules:** One idea. No intro. No "hey guys." Captions work without audio. Text overlays: max 5 words, 3-4 per reel. Batch film 4-5, change shirt between takes.

---

## Format: YouTube (7-12 min)

**Word limit:** 1500 words
**Structure:**

```
--- HOOK PHASE (0-60 sec) ---
[HOOK] Bold claim, surprising number, or pain point.
[PROOF] Specific result, not a title or bio.
[PROMISE] What they'll walk away with. Specific and measurable.
[PLAN] How the video is structured.

--- RETAIN PHASE (1-8 min) ---
[CONTENT] Chapters. Each chapter:
  - Teach: explain one thing simply
  - Show: screen share or demo
  - Result: specific number
  - Try this: what they can do right now

[PROOF STACK] Stack all results. Before/after comparison.

--- REWARD PHASE (8-10 min) ---
[REWARD] One sentence they'll remember and repeat.
[CTA] Subscribe + "Watch this next"

---
TITLE: <under 60 chars, curiosity-driven>
DESCRIPTION: <what they'll learn, who it's for, subscribe link>
CHAPTERS: <timestamps for every section>
THUMBNAIL IDEA: <visual concept>
```

**Rules:** One topic expanded deep. Every chapter needs teach + show + result. Screen recordings required. Chapter markers required. Only make YouTube about topics that proved in short-form first.

---

## Format: FB Group Post (50-100 words)

```
<value statement or result — 1-2 sentences>

<brief explanation or tip — 1-2 sentences>

<engagement question>
```

**Rules:** No links. No selling. No pitching. Pure value. End with a question. If someone asks "how?" -- reply briefly, then DM. Max 2 posts per group per week.

---

## Format: LinkedIn Post (<200 words)

**Structure:** Hook > Insight > Example > Question

---

## Format: Carousel (5-10 slides)

**Dimensions:** 1080x1080px
**Style:** White background, bold black text (Hormozi style). Use `--style light`.

```bash
python3 tools/generate_carousel.py --topic "Hook text" --slides 7 --style light --handle "@allenenriquez"
```

- Slide 1: Hook. All caps. Stop the scroll.
- Slides 2-N: One idea per slide. Max 15 words. Bold text.
- Last slide: CTA. Save, share, follow.
- No images, no gradients, no icons. Text only.

---

## Refinement Process

After generating a raw draft:

1. Read the style guide. Check hook patterns, voice rules, word banks.
2. Replace generic lines with specific metrics from the case study.
3. Tighten the hook. First line must stop the scroll.
4. Cut any sentence over 10 words. Split into two.
5. Remove all banned words (check style guide).
6. Confirm CTA or engagement question at the end.
7. Check word count against format limit.
8. Write final drafts back to `.tmp/content_drafts.json`.

## Cross-Platform Repurposing

| Source | Repurpose To |
|---|---|
| YouTube | 2-3 reels (clip key moments), 1 LinkedIn, 1 FB group post |
| Reel | LinkedIn post (text version), FB group post, carousel |
| FB group post | Reel (film the answer), LinkedIn post |

Change the hook for each platform. Don't transcribe video for text -- rewrite it.

## Rules

- NEVER post directly. Draft for Allen's review.
- NEVER use "EPS" or any client name. Use "a company", "my client", "a business I work with."
- ALWAYS include at least one specific metric in every piece.
- Simple English. 3rd grade. Short sentences. No fluff. No jargon.
- Problem first, then solution. One idea per piece.
- Never claim to be an expert or developer. Allen is learning and sharing.
- All results claimed must be real and verified.
- No selling in content. Content does the selling.

## Metrics to Reference (anonymized from day job)

- Quote turnaround: 45 min to under 5 min
- $1.6M active pipeline managed by one system
- 83 active deals tracked automatically
- 90% reduction in quote time
- Follow-up emails sent same day instead of 3 days later
- Zero leads lost to slow response since going live
