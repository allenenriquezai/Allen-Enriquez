---
name: site-visit
description: Schedule an SM8 site visit for an EPS deal. Triggers on "schedule a site visit", "book site visit", "site visit for deal", or /site-visit.
---

EPS site visit scheduler. Do NOT read any other files — everything you need is here.

## Inputs
- **Deal ID** (required) — Pipedrive deal ID
- **Date** (required) — target date for the visit. Ask if not given.
- **Staff** (optional, default: Giovanni) — who to schedule for

## How to run

Spawn a general-purpose Agent with this prompt:

> Read your instructions from `projects/eps/agents/eps-site-visit-agent.md` and follow them. Task: Schedule a site visit for deal {DEAL_ID} on {DATE}. Staff: {STAFF}.

The agent handles:
1. Fetches the deal from Pipedrive
2. Checks SM8 for an existing linked job card
3. Moves deal to Site Visit stage if needed (handles Tenders → EPS pipeline switch)
4. Waits for n8n to create SM8 job card if needed
5. Checks all 3 calendars (SM8 Paint + Clean + Google Calendar)
6. Suggests best slots, asks Allen to confirm
7. Books the site visit on SM8

## Rules
- Do NOT read agent files, memory, or workflow docs
- If user says just "site visit" without a deal, ask for the deal ID
- If no date given, ask for it
