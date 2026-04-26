# Ad Config — Coaches, Allen Self-Evidencing Campaign

Source: `tools/enriquez2.0/outreach/ad-config.coaches.allen-self.md`

This is the template config for Allen's self-run PH Meta ad campaign. Daily iterator script (`tools/personal/ad_iterator.py`) references this for voice rules, kill criteria, and hook bank.

---

## Campaign Identity

| Item | Value |
|---|---|
| **Campaign Name** | Coaches — Allen Self (PH domestic) |
| **Objective** | Leads |
| **Geography** | Philippines only |
| **Language** | English |
| **Currency** | PHP |
| **Launch Date** | TBD (setup in progress) |
| **Status** | Template (awaiting Meta account setup) |

---

## Targeting

### Primary Audience

- **Job titles / Interests:** Cohort coaching, online course creation, AI tools, Skool, GoHighLevel, ManyChat
- **Audience size cap:** 5M (PH-wide; starts narrow via exclusions)
- **Demographics:** 25–55, any gender, any income (coaches self-select on interests)
- **Exclusions:** Allen's existing followers (configured in Meta UI post-launch)

### Audience Insights

Target profile pulled from v1 coach ICP:

- Running cohort-based or community programs (Skool, Circle, custom LMS)
- 5K+ followers / audience (market awareness, authority)
- $5K–$50K/mo MRR (afford retainer, not outsourcing ops fully yet)
- Stack signals: Calendly, Stripe, ManyChat, ConvertKit, basic automation tools
- Pain: "running on fumes", "answering same DMs", "cohort drop-off", "no follow-up system"

---

## Budget & Pacing

| Item | Value |
|---|---|
| **Daily Budget** | ₱500/day × 7 days = ₱3,500 starter |
| **Weekly Budget** | ₱3,500 |
| **Monthly Target** | ₱5,000 (scales to ₱500/day after proof-of-concept) |
| **Bid Strategy** | Lowest Cost (leads objective) |
| **Billing** | Daily spend capped at ₱500 initially; scale after 2 weeks CPL data |
| **Attribution Window** | 28 days |

**Rationale:** ₱500/day tests market viability without heavy burn. At ₱5K/mo burn rate, need CPL ≤₱400 and >2 form-fills/day to sustain.

---

## Creative Rules

### Voice (Locked — from `positioning.md`)

- **Reading level:** 3rd grade (10-word sentence max)
- **Tone:** Warm-direct, operator-to-operator (peer, not guru)
- **No jargon:** Avoid "agentic workflows", "Level 4 AI", "automation"
- **Author:** Allen (sign copy as "Allen")
- **Offer:** 2-week free pilot, conditional on monthly retainer
- **System frame:** 5 connected pillars (P1 audience capture → P7 content engine), not one-off automations
- **Tech attribution:** Built on Claude Code + n8n, git-native, client-owned, no SaaS lock-in

### Ad Format

- **Platform primary:** Facebook (audience broader; link-data native)
- **Fallback:** Instagram Feed (cross-placement via Advantage+ Audience)
- **Creative type:** Single image + headline + description + CTA
- **Copy limits:**
  - Primary text (message): 125 chars soft (aim <90)
  - Headline: 40 chars max
  - Description: 90 chars max
  - CTA Button: "Book a Call" or "Learn More"

---

## Hook Bank (Source of Truth)

Reference `tools/enriquez2.0/content/icp-hooks.coaches.md` for all ad copy angles.

**Quick pull — High-leverage hooks for initial creative batch:**

| Pillar | Hook | Pain Signal |
|---|---|---|
| **P1 Audience** | "Your DMs are not a CRM. Stop pretending they are." | followers not converting, no email list |
| **P2 Trust** | "Your wins are happening. You're just not catching them." | no testimonials, no referral system |
| **P3 Sales** | "You don't need more leads. You need to stop losing the ones you have." | ghosting, no-shows, long sales cycle |
| **P4 Onboarding** | "Stripe-to-Skool handoff manual? Cohort onboarding eats 15 hours per intake." | week-1 drop-off, manual chaos |
| **P5 Ads** | "I run my own paid ads with Claude API. 24-hour creative cycles." | ads stale, CPL high, manual iteration |
| **P6 Community** | "Your DMs are eating 5 hours/week. 70% already answered in content." | drowning in support DMs |
| **P7 Content** | "I haven't posted in 3 weeks said the coach with 47 unedited Looms." | stuck in delivery, no posting rhythm |
| **System** | "Stop buying automations. Start running a system." | tools don't talk, feels fragmented |

**Daily iterator process:**

1. Pull top-performing ad from yesterday's metrics
2. Extract primary copy + hook theme
3. Generate 3 fresh variants (Claude Haiku) using voice rules above
4. Push to Meta UI as PAUSED
5. Allen manually approves + activates in UI
6. Record iteration to `ad_iterations` table

---

## KPIs & Kill Criteria

### Target Metrics

| KPI | Target | Window |
|---|---|---|
| **CPL (cost per lead)** | ≤₱400 | rolling 7-day |
| **Form-fills/day** | ≥2 | rolling 7-day |
| **Click-through rate (CTR)** | ≥0.5% | daily |
| **Cost per click (CPC)** | ≤₱5 | rolling 7-day |

### Kill Criteria (Pause Ad)

| Condition | Action |
|---|---|
| **CPL >₱400 for 3 consecutive days** | Pause ad; review copy angle |
| **0 form-fills after ₱2,000 spend** | Full pause; root-cause (creative vs audience targeting) |
| **CTR <0.3% for 5 days** | Pause + refresh creative (low relevance score incoming) |
| **CPC >₱10** | Pause (audience fatigue or poor targeting) |

**Escalation:** If 3 consecutive variants fail kill criteria → review targeting (maybe interest stack too broad) before new variant batch.

---

## Landing Page & Conversion

| Item | Value |
|---|---|
| **Landing URL** | https://allen-enriquez.github.io/ad-landing-coaches/ (placeholder — deploy pending) |
| **Form Fields** | Name, Email, Skool handle (optional), Biggest pain (required multi-select) |
| **Form CTA** | "Get the 2-week pilot plan" |
| **Post-submit** | Autoresponder (via Gmail + script): "Allen here — 30-min diagnostic call link in 2hrs" |
| **Handoff** | Form responses → Google Sheet → `tools/personal/ad_leads_ingest.py` → outreach.db (ad-lead status) |

---

## Attribution & Feedback Loop

### Daily Reporting (2am cron)

Script: `tools/personal/ad_iterator.py --campaign-id <id>`

Output to `.tmp/ad_iteration_log.jsonl`:

```json
{
  "date": "2026-04-27",
  "metrics": {
    "spend": 500,
    "impressions": 12500,
    "clicks": 75,
    "form_fills": 3,
    "cpl": 166.67,
    "top_performer_ad_id": "123456"
  },
  "actions": {
    "paused": [],
    "generated": 3,
    "pushed": 3
  },
  "next": "activate_top_3_in_ui"
}
```

### Monthly Reconciliation

Last day of month: Compare spend vs budget, CPL vs target, form-fills vs pipeline. Log to `projects/personal/data/ad_campaigns.json`.

---

## Team / Approval

| Role | Owner | Approval |
|---|---|---|
| **Script / automation** | Allen (builds ad_iterator.py) | — |
| **Creative review** | Allen | Manual UI activation (paused → active) |
| **Budget sign-off** | Allen | Real-time spend cap in Meta UI |
| **Targeting adjustments** | Allen | In Meta UI (interests, exclusions) |

No delegation until campaign hits ₱10K/mo spend (demand signal clear).

---

## Implementation Roadmap

| Phase | When | What |
|---|---|---|
| **Meta Account Setup** | Week 1 | Create ad account, verify payment method, link landing page |
| **Creative Batch 1** | Week 2 | Seed 5 initial ads (hooks from bank above) → ad_iterator template |
| **Launch** | Week 2 | Go live ₱500/day × 2 weeks = ₱7,000 test budget |
| **Iterate** | Daily | 2am: pull metrics → generate variants → push PAUSED → Allen activates |
| **Scale Decision** | Day 14 | If CPL ≤₱400 and >2 form-fills/day → increase to ₱5K/mo. Else pivot targeting/copy. |
| **Feedback to Content** | Weekly | Top-performing ad angles → feed back to `icp-hooks.coaches.md` (what resonates) |

---

## Related Files

- `tools/personal/ad_iterator.py` — Daily automation (imports this config's rules)
- `tools/enriquez2.0/content/icp-hooks.coaches.md` — Hook bank (source for copy generation)
- `projects/personal/.env` — Meta token: `META_ADS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID`
- `tools/personal/outreach_db.py` — ad-lead ingest target (form-fill capture)
- `projects/personal/offer.md` — Public offer (2-week pilot positioning)
