---
name: brief
description: Send or preview the morning briefing. Triggers on "send morning briefing", "morning brief", "send my briefing", or /brief.
---

Morning briefing via AI Executive Assistant. Do NOT read any other files — everything you need is here.

## Tool
`python3 tools/morning_briefing.py <flags>`

## Actions

### Preview (default)
```bash
python3 tools/morning_briefing.py --dry-run 2>&1 | grep -v Warning | grep -v warnings
```
Shows the HTML briefing without sending. Always preview first.

### Send
```bash
python3 tools/morning_briefing.py 2>&1 | grep -v Warning | grep -v warnings
```
Sends via personal Gmail (allenenriquez@gmail.com → allenenriquez006@gmail.com).

### Custom recipient
```bash
python3 tools/morning_briefing.py --to someone@email.com 2>&1 | grep -v Warning | grep -v warnings
```

## Flow
1. Always dry-run first and show the briefing summary
2. Ask Allen to confirm before sending
3. Send

## What it covers
- Pipedrive deals needing action (EPS)
- Gmail inbox highlights (EPS + personal)
- Calendar for today (EPS + personal)
- Two-bucket triage: Allen's Plate vs AI Can Handle

## Rules
- Do NOT read the tool source — just run it
- Do NOT read memory, workflow, or agent files
- Suppress Python warnings with the grep pipe
- If it fails, THEN read `tools/morning_briefing.py` to debug
