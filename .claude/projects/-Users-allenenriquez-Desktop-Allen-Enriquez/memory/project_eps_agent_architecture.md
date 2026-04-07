---
name: EPS AI Executive Assistant — Agent Architecture
description: Specialist subagent structure for EPS. Built 2026-04-07. Phase 2 of the AI executive assistant.
type: project
---

Phase 2 built 2026-04-07. Quote pipeline (Phase 1) is complete. Specialist agents are now live.

**Why:** Scale quoting + email to 1-2 staff, prepare for WhatsApp integration, reduce cost with Haiku specialists.

**How to apply:** When working on EPS automation, use the specialist agents — don't build monolithic workflows.

## Agent Stack

Subagent files live in `.claude/agents/` at project root.

| Agent | Model | Memory | Owns |
|---|---|---|---|
| `eps-quote-agent` | Haiku | project | Stage 0–4: intake → Google Doc |
| `eps-email-agent` | Haiku | — | Draft + send any EPS client email |
| `eps-crm-agent` | Haiku | — | Pipedrive reads, writes, deal lookups |
| `eps-qa-agent` | Haiku | project | Universal QA gate before client send |

Claude Code (Sonnet) = orchestrator. Routes automatically based on task description.

## Routing Rules
- eps-qa-agent runs before ANY client-facing output is sent
- eps-quote-agent stops after Stage 4 (Google Doc) — hands to eps-email-agent
- eps-crm-agent reads/writes Pipedrive only — no content drafting

## Follow-Up Workflow
- Workflow: `projects/eps/workflows/follow-up-email.md`
- Tool: `tools/draft_follow_up_email.py`
- Templates: `projects/eps/templates/email/follow_ups/` (4 files: builders_cleaning, builders_painting, residential_painting, residential_cleaning)
- Pattern: preview → post to Pipedrive as pinned note → Allen approves → --send

## Roadmap
- Phase 1 ✅ — Quote pipeline (Stage 0–5)
- Phase 2 ✅ — Specialist agents
- Phase 3 — WhatsApp (n8n webhook → Claude Agent SDK → same agents)
- Phase 4 — Staff access (salesperson triggers eps-quote-agent only)
