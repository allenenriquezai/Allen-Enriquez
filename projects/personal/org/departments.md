# Enriquez OS — Department Structure (Personal Brand)

Each department has: agents, a QA gate, workflows, and a folder.

## Design Principles (Priority Order)

| # | Principle | Target |
|---|---|---|
| 1 | **Less Allen Input** | System runs itself. Allen approves, not initiates. |
| 2 | **Accuracy** | 95–100%. No fabricated data. QA gates before anything public/client-facing. |
| 3 | **Speed** | Minimize latency. Fewer steps, faster execution. |
| 4 | **Cost** | As close to $0 as possible. Local over API. Batch over real-time. |
| 5 | **Scalability** | Works for 1 client or 50. No hardcoded limits. |

---

## Brand Manager (Sits Above All Departments)

**Mission:** Universal QA gate. Every piece of output passes through Brand Manager before going live.

| Agent | Role | Status | File |
|---|---|---|---|
| `personal-brand-agent` | QA gate — 3-tier review system | Future | `agents/personal-brand-agent.md` |

**3-Tier QA:**
- **Tier 1 — Auto-approve:** Routine posts, follow-ups, internal docs. No Allen needed.
- **Tier 2 — Spot-check:** Outreach to new leads, content scripts, pricing mentions. Allen sees summary, can override.
- **Tier 3 — Full review:** Client proposals, paid ads, anything with $$$ commitment. Allen approves before send.

Tiers scale down over time as accuracy proves out (Tier 2 → Tier 1, etc.).

---

## Departments

### Intelligence Unit
**Mission:** Research competitors, track ICP behavior, validate offer/pricing, track performance. Feed all other departments with data.
**Output:** `reference/intel/` (7 living docs)

| Agent | Role | Status | File |
|---|---|---|---|
| `competitor-researcher` | Track competitor content, offers, positioning | Future | `agents/competitor-researcher.md` |
| `icp-researcher` | Score ICP segments, track behavior patterns | Active | `agents/personal-icp-researcher.md` |
| `market-service` | Validate offer/pricing against market rates | Future | `agents/market-service.md` |
| `performance-analyst` | Track content/outreach/sales metrics | Future | `agents/performance-analyst.md` |

**Schedule:** Runs weekly (competitor, market) and biweekly (ICP, performance).
**Output docs (7 living docs in `reference/intel/`):**
1. Competitor landscape
2. ICP profile + scoring
3. Market rates / offer validation
4. Content performance report
5. Outreach performance report
6. Channel effectiveness
7. Trend alerts

---

### Content Production
**Mission:** Create all content — YouTube, reels, carousels, FB posts, LinkedIn. Reads intel before planning.

| Agent | Role | Status | File |
|---|---|---|---|
| `content-manager` | Orchestrator — plans calendar, assigns work, tracks production, manages research | Active | `agents/personal-content-manager.md` |
| `content-researcher` | Researches viral hooks, trending topics, competitors, audience questions | Active | `agents/personal-content-researcher.md` |
| `content-writer` | Writes scripts, posts, captions in Allen's voice | Active | `agents/personal-content-agent.md` |
| `video-editor` | Edit instructions, cuts, b-roll notes | Future | `agents/video-editor.md` |
| `visual-generator` | Thumbnails, carousels, visual assets | Future | `agents/visual-generator.md` |

**Workflows:** `content-calendar.md`, `content-formats.md`, `marketing-campaign.md`
**Rule:** Content Manager spawns content researcher BEFORE planning any content cycle. Research → Plan → Create → Post.

---

### Sales
**Mission:** Generate and convert leads. Setter model — qualify and book calls for Allen to close.

| Agent | Role | Status | File |
|---|---|---|---|
| `outreach-agent` | Cold/warm outreach — LinkedIn, FB, IG DMs | Future | `agents/outreach-agent.md` |
| `manychat` | Automated DM flows (workflow, not agent) | Future | N/A — ManyChat platform |
| `follow-up-agent` | Timed follow-up sequences for warm leads | Active | `agents/personal-followup-agent.md` |
| `lead-enrichment` | Prospect research + CRM enrichment (was research-agent) | Active | `agents/personal-research-agent.md` |
| `crm-agent` | CRM management, pipeline hygiene | Future | `agents/personal-crm-agent.md` |

**Workflows:** `outreach.md`, `follow-up-sequence.md`
**Rule:** Outreach agent reads `reference/intel/` (ICP profile, competitor landscape) before crafting messages.

---

### Delivery
**Mission:** Handle post-sale — scope, build, test, handoff. All client files in `.tmp/clients/`.

| Agent | Role | Status | File |
|---|---|---|---|
| `intake-agent` | Scopes project from discovery call notes | Future | `agents/intake-agent.md` |
| `project-manager` | Tracks milestones, deadlines, blockers | Future | `agents/project-manager.md` |
| `builder-agent` | Builds the automation / deliverable | Future | `agents/builder-agent.md` |
| `delivery-qa` | Tests deliverable before client handoff | Future | `agents/delivery-qa.md` |

**Client files:** `.tmp/clients/{client-name}/`
**Rule:** Intake reads `reference/intel/` (market rates) to validate pricing before scoping.

---

## EPS Operations (Separate Domain)

> EPS is a SEPARATE domain with its own tone, workflows, and agents. Lives in `projects/eps/`.

Organized by stage of the sales → operations lifecycle. Each department owns a stage.

### Dept 1: Lead Generation
**Mission:** Find new opportunities. Tenders, cold outreach, inbound leads.

| Agent/Tool | Role | Type |
|---|---|---|
| `eps-tender-agent` | Full E1 pipeline: scrape → docs → analyze → CRM → quote | Agent |
| `eps-cold-calls` | Cold lead batch processor — format notes → post to Pipedrive | Agent |
| `tender_batch.py` | Daily automated scrape + filter + analyze + CRM | Tool (6AM) |
| `estimateone_scraper.py` | Playwright scraper for E1 tenders + builders | Tool |
| `crm_monitor.py` | Pipeline health scan — stale deals, overdue follow-ups | Tool (EOD) |

**Workflows:** `tender-to-deal.md`, `cold-call-templates.md`

### Dept 2: Sales
**Mission:** Convert leads to won deals. Qualify, quote, follow up, close.

| Agent/Tool | Role | Type |
|---|---|---|
| `eps-crm-agent` | Pipedrive read/write — deals, contacts, notes, stages | Agent |
| `eps-quote-agent` | Quote creation — intake → line items → Google Doc | Agent |
| `eps-email-agent` | Client email drafting + sending via Gmail | Agent |
| `eps-qa-agent` | QA gate — two-stage review before anything goes to client | Agent |
| `eps-call-notes` | Post-call transcript → formatted notes → posted to deal | Agent |
| `eps-site-visit` | SM8 job link + calendar check + booking | Agent |

**Workflows:** `create-quote.md`, `calculate-line-items.md`, `measure-floor-plan.md`, `follow-up-email.md`, `deposit-process.md`, `crm-ops.md`, `qa.md`, `note-formatting.md`, `discovery-call-fields.md`

### Dept 3: Operations
**Mission:** Deliver the work. Scheduling, project tracking, data sync.

| Agent/Tool | Role | Type |
|---|---|---|
| `eps-site-visit` | Schedule site visits on SM8 | Agent (shared with Sales) |
| `crm_sync.py` | EOD Pipedrive ↔ ServiceM8 reconciliation | Tool (EOD) |
| `push_sm8_job.py` | Migrate quote data → SM8 job card | Tool |
| `schedule_sm8_visit.py` | SM8 + 3-calendar availability + booking | Tool |

**Workflows:** `deposit-process.md`, `crm-ops.md`

### Dept 4: Retention
**Mission:** Re-engage past clients. Reviews, repeat business, win-back lost deals.

| Agent/Tool | Role | Type |
|---|---|---|
| `reengage_campaign.py` | Weekly scan — clients + lost deals, draft emails | Tool (weekly) |
| `eps-email-agent` | Send re-engagement emails (shared with Sales) | Agent |

**Workflows:** `reengagement.md`

### Cross-Department (always active)
| Tool | Role | Schedule |
|---|---|---|
| `eod_ops_manager.py` | Scan ALL deals + projects → context files + questions | EOD |
| `crm_monitor.py` | Pipeline health — follow-ups, stale deals, KPIs | EOD |
| `crm_sync.py` | Pipedrive ↔ SM8 data reconciliation | EOD |
| `morning_briefing.py` | Daily briefing — actions needed, re-engagement status | 7AM |

**Context files:** `projects/eps/.tmp/deals/{id}.json` and `projects/eps/.tmp/projects/{id}.json` — one per deal/project, updated every EOD. Any agent can read these for instant context without hitting the API.

---

## Department Rules

1. Every department has a QA gate. Nothing client/public-facing ships without QA passing.
2. Agents within a department can call each other (manager delegates to writer, writer hands to QA).
3. Cross-department handoffs go through the main session (orchestrator).
4. Each department's agents reference that department's workflows — not other departments'.
5. New agents must pass `/os-gate` before going live.
6. **All departments read `reference/intel/` before doing work.** Intel is the shared brain.
7. Intelligence agents run on schedule (weekly/biweekly) — not on-demand.
8. Brand Manager QA has 3 tiers that scale down over time as trust builds.
9. Cross-department data flows through `reference/intel/` (insights) and `.tmp/` (working files).
