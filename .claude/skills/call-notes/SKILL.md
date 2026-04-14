---
name: call-notes
description: Process a call transcript for an EPS Pipedrive deal. Triggers on "process the call for deal", "format call notes", "post call notes", or /call-notes.
---

EPS call notes processor. The main session handles this directly.

## Inputs
- **Deal ID or client name** (required)
- **Call type** (optional, default: "discovery") — one of: discovery, follow-up, site-visit, general

## How to run

1. Read `projects/eps/CONTEXT.md`
2. Read `projects/eps/workflows/sales/call-notes.md` and follow it

The workflow handles:
1. Resolves deal ID (if name given)
2. Fetches transcript
3. Formats notes
4. Posts as pinned note to Pipedrive
5. On discovery calls: updates deal fields

## Rules
- If user says just "process the call" without a deal, ask for the deal ID or client name
