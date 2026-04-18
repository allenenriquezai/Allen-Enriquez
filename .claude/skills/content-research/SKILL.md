---
name: content-research
description: Content research engine — viral hooks, trending topics, competitor tracking, format trends. Triggers on "research hooks", "trending topics", "competitor content", "what's working", "content research", or /content-research.
---

Content research for Allen's personal brand. Separate from content creation.

## How to run

1. **Immediately on invoke** — load these files:
   - `projects/personal/CONTEXT.md` (brand foundation)
   - `projects/personal/reference/content-strategy-v2.md` (current strategy)
   - `projects/personal/reference/intel/icp-language.md` (audience language)
2. Check if `.tmp/content-research.md` exists — load if yes (prior research)
3. Ask Allen what to research if not clear from context
4. Follow the research workflow: `projects/personal/workflows/content/content-research.md`

## Research Types

| Allen says | Do |
|---|---|
| "hooks", "viral", "what's working" | Viral hook sweep — TikTok, IG, YT Shorts for AI/business niche |
| "competitors", "what are they posting" | Competitor tracking — check direct + adjacent creators |
| "trending", "topics" | Trending topic scan — FB groups, TikTok, comments |
| "format", "what format" | Format research — what video styles are performing |
| "ads", "paid" | Ad research — creative + copy in AI automation space |

## Output

All research writes to `projects/personal/.tmp/content-research.md` using the format defined in `projects/personal/workflows/content/content-research.md`.

## Rules
- Specific hooks, not generic advice. "This exact hook got 500K views" not "try using numbers."
- Always note source (creator, platform, approximate views)
- Focus on AI + business niche. Ignore unrelated AI content.
- Flag fast-growing creators in Allen's space
- Never fabricate view counts or engagement data
- Research BEFORE content calendar plans. Never plan blind.
