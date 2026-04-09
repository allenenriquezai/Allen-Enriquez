---
name: call-notes
description: Process a call transcript for an EPS Pipedrive deal. Triggers on "process the call for deal", "format call notes", "post call notes", or /call-notes.
---

EPS call notes processor. Do NOT read any other files — everything you need is here.

## Inputs
- **Deal ID or client name** (required)
- **Call type** (optional, default: "discovery") — one of: discovery, follow-up, site-visit, general

## How to run

Spawn the `eps-call-notes` subagent with this prompt:

> Process the latest call for deal {DEAL_ID}. Call type: {TYPE}.

Or if a name was given instead:

> Process the latest call for "{CLIENT_NAME}". Call type: {TYPE}.

The agent handles:
1. Resolves deal ID (if name given)
2. Fetches transcript via `python3 tools/fetch_call_transcript.py --deal-id DEAL_ID --call-type TYPE`
3. Formats notes using the note template
4. Posts as pinned note to Pipedrive
5. On discovery calls: also updates deal fields (address, job type, date, division)

## Rules
- Do NOT read agent files, memory, or workflow docs
- If user says just "process the call" without a deal, ask for the deal ID or client name
