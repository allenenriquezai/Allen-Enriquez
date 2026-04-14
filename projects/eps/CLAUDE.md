# EPS

EPS (Essential Property Solutions) is a painting & cleaning company based in Brisbane, Australia. Allen is the sales manager, closing ~$100K/month.

## Stack
- Pipedrive — sales CRM (pipeline, deals, quotes)
- JustCall — calls & client comms; integrated with Pipedrive
- ServiceM8 — job management for operations team
- EstimateOne — commercial tender platform (scraped daily via Playwright)
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

## Agents
Prompts in `projects/eps/agents/`. Loaded on demand by skills — NOT in `.claude/agents/`.
To use: spawn Agent with "Read your instructions from `projects/eps/agents/{agent}.md` and follow them. Task: {TASK}"

## QA Gate
Nothing client-facing without QA. Quote pipeline: draft email (no send) → QA checks doc + email together.

## Email
Gmail API (`tools/send_email_gmail.py`) from `sales@epsolution.com.au`. Auto-syncs to Pipedrive.

## Integrity
- Agents MUST fetch data from tools — fabricating = critical failure
- Agent files: target 150 lines, hard limit 200
- Incidents → `projects/eps/reference/incident-log.md`

## Tools
All in `tools/`. Run `ls tools/*.py` to see current list.
