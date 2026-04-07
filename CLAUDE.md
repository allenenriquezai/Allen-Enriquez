# Allen Enriquez — Personal OS

WAT framework: Workflows (instructions), Agents (Claude), Tools (Python scripts).

Use `/start` at the beginning of each session.

## Projects

| Folder | What it is |
|---|---|
| `projects/eps/` | Day job — EPS Painting & Cleaning, Brisbane AU |
| `projects/personal/` | Personal life + personal brand (consultancy) |

## Agent Registry

Subagents in `.claude/agents/`. Routed automatically by task.

| Agent | Handles |
|---|---|
| `eps-quote-agent` | Quote creation (intake → job description → line items → Google Doc) |
| `eps-email-agent` | Draft + send any EPS client email |
| `eps-crm-agent` | Pipedrive reads, writes, deal lookups |
| `eps-qa-agent` | QA gate before anything goes to a client |

All agents run on Haiku. Main session runs on Sonnet (orchestration only).

## Core Rules
- Check `tools/` before building anything new
- Read only files needed for the current task
- Pass data via `.tmp/` — never paste large content into context
- Ask all clarifying questions in one message upfront
- Confirm scope before running paid APIs
- Update workflows when better methods are found

## QA Gate
Nothing goes to a client — and nothing is shown to Allen for approval — until QA passes.

Quote pipeline QA is two-stage:
1. **Pre-doc** (`qa_quote.py --data-only`) — validates job description + line item math
2. **Pre-send** — draft email first (no `--send`), then QA checks quote doc + email together

## Email
Sent via Gmail API (`tools/send_email_gmail.py`) from `sales@epsolution.com.au`.
Pipedrive mailbox is read-only. Gmail auto-syncs to Pipedrive deals.
