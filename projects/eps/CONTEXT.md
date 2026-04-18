# EPS — Essential Property Solutions

Painting & cleaning company, Brisbane AU. Allen is the sales manager, closing ~$100K/month remotely from the Philippines.

## Stack

| Tool | Purpose |
|---|---|
| Pipedrive | Sales CRM — pipeline, deals, quotes |
| JustCall | Calls & client comms (integrated with Pipedrive) |
| ServiceM8 | Job management for operations team |
| EstimateOne | Commercial tender platform (scraped daily) |
| Google Drive/Docs/Sheets | Documents and data |
| Gmail API | Outbound email from sales@epsolution.com.au |

## Communication Style

Simple English. 3rd-5th grade reading level. Short sentences. Bullet points.
Straightforward, neutral, problem-focused. No fluff, no jargon.
Keep messages short and scannable. Never write long paragraphs for client comms.

## QA Gate

Nothing client-facing ships without QA passing. Order: draft email first → QA checks doc + email together → Allen approves → send.

## Pipelines

| Pipeline | ID | Division |
|---|---|---|
| EPS Clean | 1 | Cleaning |
| EPS Paint | 2 | Painting |
| Tenders - Clean | 3 | Cleaning (tenders) |
| Tenders - Paint | 4 | Painting (tenders) |

Separate deals per division. Never put paint + clean on the same deal.

## Workflows (by department)

### Lead Generation — `workflows/lead-gen/`
- `tender-pipeline.md` — E1 scrape → analyze → CRM → quote
- `cold-calling.md` — batch process cold call sessions

### Sales — `workflows/sales/`
- `create-quote.md` — full quoting pipeline (intake → doc → email → QA)
- `follow-up-email.md` — follow-up emails for quiet deals
- `call-notes.md` — fetch transcript → format → post to Pipedrive
- `site-visit.md` — SM8 site visit scheduling
- `qa.md` — QA checks for quotes and emails
- `note-formatting.md` — note template reference
- `discovery-call-fields.md` — fields to populate on discovery calls

### Operations — `workflows/operations/`
- `crm-ops.md` — Pipedrive API patterns, pipeline/stage IDs, field keys
- `deposit-process.md` — post-acceptance deposit + SM8 push

### Retention — `workflows/retention/`
- `reengagement.md` — re-engage past clients and lost deals

## Tools

All Python scripts in `tools/`. Run `ls tools/*.py` to see current list.

## Environment

- Credentials: `projects/eps/.env`
- Temp files: `projects/eps/.tmp/`
- Job descriptions: `projects/eps/job_descriptions/`
- Pricing: `projects/eps/config/pricing.json`
- Email templates: `projects/eps/templates/email/`

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
- Failures → `projects/eps/reference/incident-log.md`
- New code/tool → run `/os-gate`. Check `tools/` before building new.
- Session end → `/wrap` handles handoff + decision log

## Integrity

- Always fetch data from tools — fabricating data is a critical failure

## Correction Loop

When Allen corrects your work on any EPS task:
1. Fix the immediate issue
2. Open the workflow file you were following
3. Add the correction as a permanent rule with a short "Why"
4. Confirm: "Fixed. Updated [workflow] so this won't happen again."
