# EPS

EPS (Essential Property Solutions) is a painting & cleaning company based in Brisbane, Australia. Allen is the sales manager, closing ~$100K/month. Automation is early-stage.

## Stack
- Pipedrive — sales CRM (pipeline, deals, quotes)
- JustCall — calls & client comms for sales team; integrated with Pipedrive
- ServiceM8 — job management for operations team
- WhatsApp — team comms
- Google Drive / Docs / Sheets — documents and data

## Environment
Credentials: `projects/eps/.env`
Workflows: `projects/eps/workflows/`
Temp files: `projects/eps/.tmp/`

## Communication Style
Spartan. Simple English (3rd–5th grade reading level). Bullet points.
Straightforward, neutral, problem-focused. No fluff, no jargon.

- Focus on the client's problem, not features
- Keep messages short and scannable
- Bullet points for any written client-facing output
- Never write in long paragraphs for comms

## Workflows
- `prospect-research.md` — find and qualify painting companies
- `manage_google_sheet.md` — read/write prospect data to Sheets
- `scrape_bbb.md` — scrape BBB for company data
