---
name: cold-calls
description: Process EPS cold calls after a calling session. Triggers on "process my cold calls", "process cold calls", or /cold-calls.
---

EPS cold call batch processor. The main session handles this directly.

## How to run

1. Read `projects/eps/CONTEXT.md`
2. Read `projects/eps/workflows/lead-gen/cold-calling.md` and follow it

The workflow handles the full pipeline:
1. Fetches batch via `python3 tools/process_cold_calls.py fetch --verbose`
2. Filters connected vs not-connected leads
3. Formats notes for each connected lead
4. Drafts emails for warm leads
5. Posts notes to Pipedrive
6. Shows email drafts to Allen for approval

## Rules
- Do NOT send emails — only draft and show for approval
- If fetch returns 0 leads, report that and stop
