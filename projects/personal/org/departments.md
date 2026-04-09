# Enriquez OS — Department Structure

Each department has: agents, a QA gate, workflows, and a folder.

## Departments

### Marketing
**Mission:** Build brand awareness, generate inbound leads, grow audience.
**Scope:** Content creation (reels, YouTube, FB), social media, outreach, brand voice.

| Agent | Role | Status |
|---|---|---|
| `personal-content-manager` | Orchestrator — plans calendar, tracks production, assigns work | Active |
| `personal-content-agent` | Copywriter — writes scripts and posts in Hormozi style | Active |
| `personal-style-researcher` | Style analyst — builds and maintains style guides | Active |
| `personal-marketing-qa` | QA gate — reviews all content before posting | Active |

**Workflows:** `marketing-campaign.md`, `content-formats.md`, `fb-group-outreach.md`, `content-calendar.md`
**Tools:** `generate_content.py`, `content_tracker.py`, `research_content_style.py`
**Reference:** `hormozi-style-guide.md`

---

### Sales
**Mission:** Convert leads to paying clients. Manage pipeline and follow-ups.
**Scope:** CRM, prospecting, cold outreach, follow-up sequences, closing.

| Agent | Role | Status |
|---|---|---|
| `personal-research-agent` | Prospect enrichment — fills CRM with hooks before calls | Active |
| `personal-followup-agent` | Follow-up sequencer — sends timed emails to warm leads | Active |
| `personal-sales-qa` | QA gate — reviews outreach before sending | Future |

**Workflows:** `follow-up-sequence.md`, `crm-daily-review.md`
**Tools:** `personal_crm.py`, `research_prospect.py`, `enrich_prospects.py`, `send_personal_email.py`

---

### Product
**Mission:** Build and improve Enriquez OS itself.
**Scope:** New agents, tools, workflows, automation, system reliability.

| Agent | Role | Status |
|---|---|---|
| Main session (Allen + Claude) | Architect and builder | Active |

**Workflows:** OS gate (`/os-gate`), decision log (`DECISIONS.md`)
**Tools:** All `tools/` scripts

---

### Operations (EPS)
**Mission:** Deliver client work — quotes, emails, job management.
**Scope:** Quote pipeline, client comms, CRM, call processing.

| Agent | Role | Status |
|---|---|---|
| `eps-quote-agent` | Quote creation pipeline | Active |
| `eps-email-agent` | Client email drafting and sending | Active |
| `eps-crm-agent` | Pipedrive CRM specialist | Active |
| `eps-qa-agent` | QA gate — reviews quotes and emails | Active |
| `eps-call-notes` | Call transcript processor | Active |
| `eps-cold-calls` | Cold lead batch processor | Active |

**Workflows:** `create-quote.md`, `calculate-line-items.md`, `measure-floor-plan.md`, `cold-call-templates.md`
**Tools:** `calculate_quote.py`, `qa_quote.py`, `send_email_gmail.py`, `fetch_call_transcript.py`, `process_cold_calls.py`

---

### Support
**Mission:** Handle client questions, troubleshooting, onboarding.
**Scope:** Client comms post-sale, issue resolution, FAQ.

| Agent | Role | Status |
|---|---|---|
| (Future) | TBD | Future |

---

## Department Rules
1. Every department has a QA gate. Nothing client/public-facing ships without QA passing.
2. Agents within a department can call each other (manager delegates to writer, writer hands to QA).
3. Cross-department handoffs go through the main session (orchestrator).
4. Each department's agents reference that department's workflows — not other departments'.
5. New agents must pass `/os-gate` before going live.
