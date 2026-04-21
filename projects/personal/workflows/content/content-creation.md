# Content Creation — Writing SOP

Write reel scripts, YouTube scripts, FB group posts, LinkedIn posts. All content follows Hormozi style.

## Rule: Never fabricate proof lines

Never insert "I use [tool] to [result]" lines without verifying Allen has actually done that with that specific tool. Allen's automation results (1.6M pipeline, 80+ deals, $60-100K/mo) came from his full stack — not specifically Claude. Claude use started ~April 2026, so any "I use Claude to..." claim must match that timeline + his real use.

**How to apply:** Before writing any "I / my system" proof line in a script, check: (1) does the claim match the specific tool in the script? (2) does the timeline match Allen's actual use? If unsure, ask Allen for the real metric or leave proof out entirely. Audience smells borrowed authority instantly — Allen has zero clients and can't afford trust damage.

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

> **Format structures** (Reel, YouTube, FB Group, LinkedIn): see `reference/hormozi-style-guide.md`

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

## Captions + Hashtags

See `captions.md` for platform-specific caption generation SOP. Hybrid method: viral reference modeling + platform meta rules + voice filter.

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
- **EVERY piece must teach AI sales automation.** The niche is AI-powered sales systems. Not generic sales tips. Not generic AI tips. Content must show how AI automates a specific sales task. If the viewer can't connect it to AI + sales, it's off-brand.
- **Content must come from Allen's real systems.** Before writing, check what tools exist in `tools/`, what automations run in `automation/`, and what workflows Allen actually uses. Teach from real systems, not hypotheticals. Why: Allen's unfair advantage is he actually uses this stuff daily — content must reflect that.
- **Only claim what Allen has lived.** Allen has ONE automated business — his own. No "I see businesses doing X" or citing market stats as if they're personal experience. Every claim must trace back to something Allen built, broke, fixed, or learned firsthand. Why: Allen has zero clients yet. Audience will smell borrowed authority instantly.
- **Follow the SOP structure exactly.** Don't freestyle scripts. Use the format templates above (Hook+Proof → Promise → Content → CTA). Why: freestyled scripts drift into "look at me" flexing instead of delivering teachable value.
- **60 seconds is a guideline, not a cap.** If the hook is strong and the content delivers real value, 90-120 sec is fine. Completion rate matters more than raw length. Don't pad to fill time, don't cut value to hit 60 sec.

## Metrics to Reference (anonymized from day job)

- Quote turnaround: 45 min to under 5 min
- $1.6M active pipeline managed by one system
- 83 active deals tracked automatically
- 90% reduction in quote time
- Follow-up emails sent same day instead of 3 days later
- Zero leads lost to slow response since going live
