# EPS

EPS (Essential Property Solutions) is a painting & cleaning company based in Brisbane, Australia. Allen is the sales manager, closing ~$100K/month.

## Stack
- Pipedrive — sales CRM (pipeline, deals, quotes)
- JustCall — calls & client comms; integrated with Pipedrive
- ServiceM8 — job management for operations team
- WhatsApp — team comms
- Google Drive / Docs / Sheets — documents and data

## Environment
Credentials: `projects/eps/.env`
Temp files: `projects/eps/.tmp/`

## Communication Style
Spartan. Simple English (3rd-5th grade reading level). Bullet points.
Straightforward, neutral, problem-focused. No fluff, no jargon.
- Focus on the client's problem, not features
- Keep messages short and scannable
- Never write in long paragraphs for comms

## Agent Registry

Subagents in `.claude/agents/`. All run on Haiku.

| Agent | Handles |
|---|---|
| `eps-quote-agent` | Quote creation (intake → line items → Google Doc) |
| `eps-email-agent` | Draft + send any EPS client email |
| `eps-crm-agent` | Pipedrive reads, writes, deal lookups |
| `eps-qa-agent` | QA gate before anything goes to a client |
| `eps-call-notes` | Post-call: fetch transcript → format notes → post to deal |
| `eps-cold-calls` | Cold lead batch processor: format notes → post to person |

## QA Gate
Nothing goes to a client until QA passes.

Quote pipeline QA is two-stage:
1. **Pre-doc** (`qa_quote.py --data-only`) — validates job description + line item math
2. **Pre-send** — draft email first (no `--send`), then QA checks quote doc + email together

## Email
Sent via Gmail API (`tools/send_email_gmail.py`) from `sales@epsolution.com.au`.
Pipedrive mailbox is read-only. Gmail auto-syncs to Pipedrive deals.

## System Integrity
- Agents MUST fetch data from tools — fabricating data is a critical failure
- Agent files: target 150 lines, hard limit 200. If over, split.
- All `tools/*.py` references in agents must resolve to real files
- Incidents logged in `projects/eps/reference/incident-log.md`

## Key Tools
- `fetch_call_transcript.py` — fetch JustCall transcript for a Pipedrive deal
- `process_cold_calls.py` — batch fetch/post for cold outreach leads
- `send_email_gmail.py` — send emails via EPS Gmail
- `calculate_quote.py` — pricing engine
- `qa_quote.py` — quote QA checker
