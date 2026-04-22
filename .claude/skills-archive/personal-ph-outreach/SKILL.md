---
name: personal-ph-outreach
description: PH market outbound outreach — discover prospects, enrich, generate queue, log sent, track follow-ups, draft replies. Triggers on "PH outreach", "PH prospects", "today's queue", "outreach queue", "log sent", "followups due", "outreach stats", "draft replies", or /personal-ph-outreach.
---

PH outbound outreach system. Automates discover -> enrich -> queue -> follow-up -> reply-draft. Allen reviews + sends manually.

## Tool
`python3 tools/outreach.py <subcommand>`

## Sheet
[PH Outreach](https://docs.google.com/spreadsheets/d/15NvyLkAWya3ZNxT-R1dSPTVN1z2CyKEzDTdfxHY38Do/edit)

## Inbox file (where Allen drops FB/IG URLs)
`projects/personal/.tmp/fb_prospects_inbox.txt`

## Actions

Parse Allen's request and run the matching command. If unclear, ask.

### stats (default)
"show stats", "where am I", "outreach stats", "how many prospects"
```bash
python3 tools/outreach.py stats
```
Print output directly.

### discover
"run discover", "find prospects", "pull new leads", "weekly discover"
```bash
python3 tools/outreach.py discover --segment recruitment --dry-run  # preview
python3 tools/outreach.py discover --segment recruitment            # write to sheet
```
Segments: `recruitment`, `real_estate`. Omit `--segment` to run both. Optional `--source` = `places`, `businesslist`, `jobstreet`, `kalibrr`, `fb_inbox`. Always dry-run first if Allen hasn't said "just run it".

### enrich
"enrich prospects", "fill in data", "add personal hooks"
```bash
python3 tools/outreach.py enrich --limit 10 --dry-run  # preview one
python3 tools/outreach.py enrich --limit 10
```
Dry-run first to show what would change.

### queue
"build today's queue", "generate outreach queue", "what am I sending"
```bash
python3 tools/outreach.py queue
```
Writes `projects/personal/.tmp/outreach_queue_YYYY-MM-DD.md`. Read it back and show Allen a count + first message preview.

### log-sent
"mark sent 1,3,5", "I sent 1 through 8", "log sent 1,2,3"
```bash
python3 tools/outreach.py log-sent --ids 1,2,3
```
Allen gives row IDs from today's queue. Echo the result count.

### followups
"check followups", "any followups today", "who needs touch 2"
```bash
python3 tools/outreach.py followups
```
Print list directly.

### replies
"check replies", "draft replies", "anyone reply"
```bash
python3 tools/outreach.py replies
```
Drafts land in `projects/personal/.tmp/reply_drafts.md`. Read + summarise for Allen.

## Rules
- Run from repo root: `cd "/Users/allenenriquez/Desktop/Allen Enriquez"`
- Do NOT read `tools/outreach.py` or the 4 modules — just run the CLI
- Do NOT read memory files, CLAUDE.md, workflow docs — this skill is self-contained
- Suppress Python warnings: pipe through `2>&1 | grep -v -E "Warning|warnings.warn|google-auth|api_core|Google will"` for clean output
- For destructive ops (discover writing to sheet, log-sent updating sheet), confirm with Allen first unless he said "just do it"
- If command fails, THEN read relevant module to debug

## Guardrails (inform Allen, don't bypass)
- Send stays manual — no auto-send
- Email cap per day: 3/5/8/10/15 warmup ramp (week 1 -> 5)
- FB DM cap: 12/day hard limit
- No FB group member scraping (ban risk)
