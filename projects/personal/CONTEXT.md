# Personal — Allen Enriquez

Two areas: personal brand (AI automation educator + service provider) and personal life automations.

## Allen's Story

Sales manager at EPS Painting & Cleaning (Brisbane, AU). Employee, not owner. Works remotely from the Philippines. ~1 year at EPS.

**Team:** Giovanni is director. Dexter is a sales rep (PH-based) who helps with quotes + customer service. NOT a solo operation.

**Results (verified):**
- $60-100K/month in new revenue (him + assistant)
- Best month: $114K (Feb 2026) — closed without a single face-to-face meeting
- Built full AI agent system: quotes, follow-ups, emails, CRM, scheduling
- Quotes went from ~45 min to ~5 min
- Manages 80+ active deals with AI (sales team: Allen + Dexter)
- No sales meetings in 3 months — systems handle the process

**Who Allen is:** NOT a sales expert or natural closer. Wins through SYSTEMS, SPEED, and CONSISTENCY. Self-taught everything. Sales background, not engineering. Allen's self-assessment: "I'm not really good at sales. I'm not a tech expert. But I'm not afraid of following up. I'm not afraid of failing. I work hard. I'm very critical."

**Automation timeline:** Few months with n8n (quote builder, speed-to-lead, basic CRM). Started Claude Code April 2026 — full agent system built in ~2 weeks. n8n is legacy/background. The story is Claude Code now. System is live and running, not "still building."

**What's true vs aspirational:**
- TRUE: revenue numbers, automation timeline, tools used, deal stories
- ROUGH ESTIMATES: "20 hrs saved/week" (not tracked), "45 min to 5 min quotes" (approximate)
- ASPIRATIONAL: AI consultancy (pre-revenue, zero clients yet), SaaS product (long-term)
- NEVER CLAIM: that Allen owns EPS, that he's a developer/engineer, that he has paying consulting clients yet

## Niche

AI-powered sales systems. One niche, one year. How to use AI to sell more, follow up faster, never lose a deal, spend zero time on admin.

> **V2 (April 2026):** Widened to "AI for business/work people." V1 niche stays as proof lane (30%). Full strategy: `reference/content-strategy-v2.md`

## The Offer

**Free:** Content showing how Allen builds AI sales systems for his real job. Full tutorials, real examples, hold nothing back.
**Paid (Phase 1):** Done-for-you AI sales system setup. First 3-5 clients free for testimonials. Pricing TBD — market benchmarks $2K-$8K setup + $500-$1K/month.
**Paid (Phase 2):** Community/education (Skool). Only after 5-10 paying clients.
**Long-term:** SaaS — productise the AI sales system.

**Soft CTA:** "Everything on this channel is free. You can do all of this yourself. If you don't have the time — let me know and I'll help you set it up for free."

## ICP

### Content Audience (broad)
| Segment | Why they follow |
|---|---|
| Filipino VAs | Fear of AI replacement, need to upskill |
| Professionals (realtors, recruiters, coaches) | Want to work smarter |
| Service business owners | Drowning in admin |
| Content creators | Want posting/outreach systems |

### Customers (narrow — emerges from audience)
| Segment | What they buy |
|---|---|
| Service businesses (trades, real estate, coaching) | Sales automation: CRM, follow-ups, quotes |
| Content creators with budget | Content systems: auto-posting, scheduling |
| Professionals who'd rather pay than DIY | Whatever system solves their biggest time sink |

**Strategy:** PH market first for credibility + testimonials → AU/US/UK for paid clients at Western rates.

### First Clients (April 2026)
1. Sinan Abu Aisheh — coach in AU, already uses AI
2. Realtor friend — PH real estate, big connections
3. Car flipper/painter friend — PH auto body + active content creator

## Voice

Based on Alex Hormozi's content principles. Non-negotiable.

- 3rd grade reading level. If a 9-year-old can't understand it, rewrite.
- Max 10 words per sentence. Break long thoughts into two.
- No jargon. No filler. No corporate speak.
- Confident but not arrogant. Direct. Say what you mean.
- Use "you" and "I". Never "one" or "we" (unless talking about a team).

**Use:** simple, free, fast, easy, money, time, save, lose, stop, start, help, build, grow, fix, break, work, try, real, true
**Never use:** leverage, utilize, synergy, optimize, paradigm, scalable, ecosystem, ideate, disrupt, holistic, pivot, bandwidth, deep-dive, circle back, low-hanging fruit, value-add, stakeholder

**Hook patterns:** Bold claim, Pattern interrupt, Number hook, Story hook, Question hook, Contrarian, Result hook

## Positioning

Allen IS: a sales guy learning AI and sharing everything. Proof that you don't need to be technical.
Allen is NOT: an AI expert, a developer, someone selling courses, a build-in-public channel.
**Core message:** "I'm not a tech guy. I'm a sales guy who got tired of doing the same tasks every day. So I built AI to do them for me."

## Workflows (by department)

### Intelligence — `workflows/intel/`
- `icp-research.md` — audience language, pain points, buying behavior
- `competitor-research.md` — track competitor content and positioning
- `market-analysis.md` — validate offer/pricing against market
- `performance-analysis.md` — track content/outreach/sales metrics

### Content Production — `workflows/content/`
- `content-calendar.md` — plan, track, and manage content production
- `content-creation.md` — write scripts, posts, captions
- `content-research.md` — viral hooks, trending topics, competitor intel
- `content-formats.md` — format-specific rules and templates
- `video-editing.md` — edit instructions and specs

### Sales — `workflows/sales/`
- `outreach.md` — cold/warm outreach across platforms
- `follow-up.md` — timed follow-up sequences

### Delivery — `workflows/delivery/`
- `client-intake.md` — scope projects from discovery calls
- `project-build.md` — build the automation deliverable
- `project-management.md` — track milestones and deadlines
- `delivery-qa.md` — test before client handoff

## Design Principles

**Take action.** Build it, ship it, QA it, iterate. Every session moves something forward.

| # | Principle | Target |
|---|---|---|
| 1 | **Less Allen Input** | System runs itself. Allen approves, not initiates. Fewer questions, more action. |
| 2 | **Accuracy** | 95-100%. No fabricated data. QA gates before client output. Fail loud, never silent. |
| 3 | **Speed** | Fewer steps, faster execution, less waiting. |
| 4 | **Cost** | As close to $0 as possible. Local over API. Batch over real-time. |
| 5 | **Scalability** | Works for 1 quote or 50. No hardcoded limits. |

Priority order when trade-offs arise: Less Input > Accuracy > Speed > Cost > Scalability.

## Behavior

- **Push Allen.** Surface content buffer, outreach pace, pending replies, stale intel at session start.
- Figure out what Allen means. Don't ask unnecessary questions.
- Pass data via `.tmp/` — never paste large content into context.
- Check `.tmp/pending_inquiries.json` at session start — surface if items exist.
- Confirm scope before running paid APIs.
- Read only files needed for the current task.
- **End of session:** when Allen says "done" / "that's it" / wraps up → automatically run `/wrap`.

## Change Tracking

- Decisions → `DECISIONS.md` + update relevant files
- New code/tool → run `/os-gate`. Check `tools/` before building new.
- Session end → `/wrap` handles handoff + decision log

## Brand Context — Tiered Loading

CONTEXT.md is the brand foundation. Always loaded. Additional files load by task type:

| Task | Also load |
|---|---|
| Write content (scripts, posts) | `reference/hormozi-style-guide.md` + `workflows/content/content-creation.md` + `intel/icp-language.md` |
| Content calendar/planning | `workflows/content/content-creation.md` |
| Research (ICP, competitor, market) | `intel/icp-language.md` + `intel/competitor-moves.md` |
| Outreach / follow-up | `intel/icp-language.md` |
| Content research (hooks, trends) | `.tmp/content-research.md` + `intel/icp-language.md` |

Memory files (content_profile, sales_identity, content_models) are auto-loaded by Claude's memory system — do NOT manually read them.

Any file can still be pulled mid-session if needed. Tiering controls upfront loading, not access.

**Why:** Allen should never have to teach a session what it already has access to. These files contain his real story, his team, his positioning, his voice. Getting any of this wrong breaks trust with the audience.

## Correction Loop

When Allen corrects your work on any personal brand task:
1. Fix the immediate issue
2. Open the workflow file you were following
3. Add the correction as a permanent rule with a short "Why"
4. Confirm: "Fixed. Updated [workflow] so this won't happen again."
