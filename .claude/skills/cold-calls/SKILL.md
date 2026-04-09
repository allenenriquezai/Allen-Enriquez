---
name: cold-calls
description: Process EPS cold calls after a calling session. Triggers on "process my cold calls", "process cold calls", or /cold-calls.
---

EPS cold call batch processor. Do NOT read any other files — everything you need is here.

## What it does
After a calling session, fetches recently called leads, formats notes, drafts emails for warm leads.

## How to run

Spawn a general-purpose Agent with this prompt:

> Read your instructions from `projects/eps/agents/eps-cold-calls.md` and follow them. Task: Process Allen's cold calls from the latest calling session.

The agent handles the full pipeline:
1. Fetches batch via `python3 tools/process_cold_calls.py fetch --verbose`
2. Filters connected vs not-connected leads
3. Formats notes for each connected lead
4. Drafts emails for Asked For Email + Warm Interest leads
5. Posts notes to Pipedrive via `python3 tools/process_cold_calls.py post --lead-id LEAD_ID`
6. Shows email drafts to Allen for approval

If the user specifies `--limit N`, pass it to the fetch command.

## Rules
- Do NOT read agent files, memory, or workflow docs
- Do NOT send emails — only draft and show for approval
- If fetch returns 0 leads, report that and stop
