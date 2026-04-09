---
name: crm
description: Personal brand CRM — report, cleanup, brief, draft. Triggers on "CRM report", "clean up my CRM", "evening brief", "draft email for lead", or /crm.
---

Personal Brand CRM tool. Do NOT read any other files — everything you need is here.

## Tool
`python3 tools/personal_crm.py <subcommand>`

## Sheet Structure
10 tabs: `Paint | Call Queue`, `Paint | Warm Interest`, `Paint | Callbacks`, `Paint | Emails Sent`, `Paint | Not Interested` — same for `Other |`.

## Actions

Parse the user's request and run the matching command. If unclear, ask.

### report (default if no action specified)
```bash
python3 tools/personal_crm.py review
```
Print the output directly. If the user asks about a specific date's calls, read `.tmp/personal_crm.json` and filter by `date_called`.

### cleanup
```bash
python3 tools/personal_crm.py cleanup --dry-run   # preview first
python3 tools/personal_crm.py cleanup              # apply
```
Always dry-run first, show changes, then ask to apply.

### brief
```bash
python3 tools/personal_crm.py evening-brief --dry-run   # preview
python3 tools/personal_crm.py evening-brief              # send
```
Always dry-run first. Show subject line + action count. Ask before sending.

### draft
```bash
python3 tools/personal_crm.py draft --row <N> --tab "<tab name>"
```
User must specify which lead. Tab defaults to `"Paint | Call Queue"` if not given.

### reorganize
```bash
python3 tools/personal_crm.py reorganize --dry-run
python3 tools/personal_crm.py reorganize
```
One-time migration. Always dry-run first.

### dedupe
```bash
python3 tools/personal_crm.py dedupe-phone --dry-run
python3 tools/personal_crm.py dedupe-phone
```
Always dry-run first.

## Rules
- Run commands from the repo root: `cd "/Users/allenenriquez/Desktop/Allen Enriquez"`
- Do NOT read `tools/personal_crm.py` — just run it
- Do NOT read memory files, CLAUDE.md, or workflow docs
- Suppress Python warnings: pipe through `2>&1 | grep -v Warning | grep -v warnings` for cleaner output
- If a command fails, THEN read the relevant section of the tool to debug
