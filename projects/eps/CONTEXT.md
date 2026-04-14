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

## Integrity

- Always fetch data from tools — fabricating data is a critical failure
- Incidents → `projects/eps/reference/incident-log.md`

## Correction Loop

When Allen corrects your work on any EPS task:
1. Fix the immediate issue
2. Open the workflow file you were following
3. Add the correction as a permanent rule with a short "Why"
4. Confirm: "Fixed. Updated [workflow] so this won't happen again."
