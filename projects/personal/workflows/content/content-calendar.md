# Content Calendar — Planning & Tracking SOP

Plan content, track production, surface daily assignments. This is the command center for Allen's 30-day content campaign.

## Tools

| Tool | Command |
|---|---|
| Init campaign | `python3 tools/content_tracker.py init --days 30 --start YYYY-MM-DD` |
| Today's assignments | `python3 tools/content_tracker.py today` |
| Campaign status | `python3 tools/content_tracker.py status` |
| Full report | `python3 tools/content_tracker.py report` |
| Mark progress | `python3 tools/content_tracker.py mark --day <N> --type <reel\|youtube> --slot <1\|2> --status <filmed\|posted>` |
| Set topic | `python3 tools/content_tracker.py topic --day <N> --type <youtube\|reel> --text "Topic"` |
| Generate scripts | `python3 tools/generate_content.py --batch-day <N>` |
| Generate carousel | `python3 tools/generate_carousel.py --topic "Hook text" --slides 5 --style dark --handle "@allenenriquez"` |

## Campaign Init

If no tracker exists at `projects/personal/.tmp/content_tracker.json`:
1. Run the init command
2. Load topics from the topic backlog (below)
3. Assign pillars to days using the rotation

## Daily Briefing ("What do I film today")

Run `content_tracker.py today`. Show Allen:
- Which 2 reels and 1 YouTube are assigned
- Script status (scripted / needs writing)
- Any FB group posts scheduled
- Which reel should become a carousel

If scripts are missing, generate them and present raw drafts. Flag they need refinement via the content-creation workflow.

## Status Tracking

Run `content_tracker.py status`. Show:
- Posted / filmed / scripted counts
- Days behind (if any)
- "You're 3 days behind on filming" is helpful. Paragraphs are not.

## Marking Progress

When Allen says something is filmed or posted:
```bash
python3 tools/content_tracker.py mark --day <N> --type reel --slot 1 --status filmed
python3 tools/content_tracker.py mark --day <N> --type youtube --status posted
```

## Content Pillars (Rotate Daily)

| Day | Pillar | SPCL Focus |
|---|---|---|
| Mon | AI automation results | Status + Credibility |
| Tue | How-to tutorials | Power |
| Wed | Business pain points | Likeness |
| Thu | Behind the scenes | Likeness + Credibility |
| Fri | Contrarian takes | Status + Power |
| Sat | Quick wins | Power |

Don't post the same pillar two days in a row.

## Posting Schedule

3 videos/day. Each video goes to all platforms + carousel.

| Slot | PH Time | Best For |
|---|---|---|
| Video 1 | 7:00 AM | US evening + AU morning |
| Video 2 | 2:00 PM | AU afternoon + UK morning |
| Video 3 | 8:00 PM | US morning + UK afternoon |

Per video cross-post: TikTok (original) > FB Reels + IG Reels (same time) > YT Shorts + LinkedIn (+1h) > IG Carousel + FB Carousel (+2h).

**Total daily output:** 3 videos x 7 platforms = 21 posts.
**YouTube long-form:** 12:00 PM Saturday (from week 3).
**FB group value posts:** Tue + Thu + Sat.

## Carousel Repurposing

Every reel becomes a carousel. Same idea, reading format.
```bash
python3 tools/generate_carousel.py --topic "Hook text" --slides 5-7 --style dark --handle "@allenenriquez"
```
- Slide 1: Hook (bold, stop the scroll)
- Slides 2-5: One point per slide. Max 15 words.
- Last slide: CTA

## FB Group Outreach Planning

- 2-3 value posts/week across all groups
- Max 1 post per group per week
- Best days: Tue, Thu, Sat (8-10 AM PH)
- Post types: quick wins, result shares, questions, education
- End every post with a question
- Generate: `python3 tools/generate_content.py --type fb-group-post --topic "<topic>"`

## Research Before Planning

**Rule: never plan a content batch without checking research first.**

Read `projects/personal/.tmp/content-research.md` before planning each week. If stale or missing, trigger the content-research workflow first.

## Campaign Phases

| Phase | When | Focus |
|---|---|---|
| Volume Sprint | Week 1 | 1-2 short-form/day. Hook + value. Find voice. Build engagement data. |
| Mini Tutorials | Week 2+ | 2 short-form/day. Screen recordings. Teach real systems step-by-step. |
| Add YouTube | Week 3+ | Continue 2/day + 1 YouTube long-form/week. Topic = best short-form. |
| Optimize | Month 2+ | Review performance. Double down on winners. Test FB ads. |

## Topic Backlog

**Proof + Value:** Quote automation (45min to 5min), $114K month, AI daily briefing, follow-up automation.
**Deep Tutorials:** What AI agents are, prompts explained, Claude Code from zero, first automation in 5min, CRM + AI agents.
**Learn in Public:** Discoveries, broken automations, mistakes, 6-month honest review.
**Relatable:** VAs who learn AI get 3x, $50/month stack, not a tech guy, stop manual follow-ups.
**Vision:** Small teams beat big teams, AI won't replace you but someone using AI will.

## Metrics to Track

**Weekly:** Views per video, best performer (topic + hook), saves/shares, comments, DMs.
**YouTube (from week 3):** Watch time, retention, CTR, subscriber growth.
**Monthly:** Total followers, produced vs planned, outreach DMs + reply rate, leads generated.
