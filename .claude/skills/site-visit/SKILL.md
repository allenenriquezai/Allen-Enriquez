---
name: site-visit
description: Schedule an SM8 site visit for an EPS deal. Triggers on "schedule a site visit", "book site visit", "site visit for deal", or /site-visit.
---

EPS site visit scheduler. The main session handles this directly.

## Inputs
- **Deal ID** (required)
- **Date** (required — ask if not given)
- **Staff** (optional, default: Giovanni)

## How to run

1. Read `projects/eps/CONTEXT.md`
2. Read `projects/eps/workflows/sales/site-visit.md` and follow it

The workflow handles:
1. Fetches deal from Pipedrive
2. Checks SM8 for existing job card
3. Moves deal to Site Visit if needed
4. Checks all 3 calendars
5. Suggests slots, Allen confirms
6. Books on SM8

## Rules
- If user says just "site visit" without a deal, ask for deal ID
- If no date given, ask for it
