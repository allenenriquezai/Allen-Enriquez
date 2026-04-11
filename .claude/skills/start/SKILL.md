---
name: start
description: Use at the beginning of each session to load minimal context, resume from last handoff, and push Allen.
disable-model-invocation: true
---

Start the session lean — load only what's needed, then push Allen with status.

## Step 1: Load Handoffs

Read ALL handoff files (Allen runs parallel sessions):
- `projects/eps/.tmp/session_handoff.md`
- `projects/personal/.tmp/session_handoff.md`
Skip any that don't exist. Do not error.

## Step 2: Check Queues

- Read `.tmp/pending_inquiries.json` if it exists
- If items exist, note the count (don't list details yet)

## Step 3: Push Allen Dashboard

Run these checks and print a status dashboard:

### Intel Freshness
Check `last_updated` date in each file in `projects/personal/reference/intel/`. Flag any older than 7 days (14 days for `market-validation.md`). Format:
```
Intel: 3/7 docs fresh | STALE: competitor-moves.md (12d), icp-language.md (9d)
```
If all fresh: `Intel: 7/7 docs fresh`

### Content Buffer
Check `projects/personal/.tmp/content-buffer.json` if it exists. Show:
```
Content buffer: X weeks ahead | [RAW RECORDINGS: N] [SCRIPTS READY: N] [PUBLISHED: N]
```
If no buffer file exists: `Content buffer: No data — record first batch to start tracking`

### Outreach Pace
Check `projects/personal/.tmp/outreach_log.jsonl` if it exists. Count entries from last 7 days:
```
Outreach: X DMs sent this week (target: 210/week) | Reply rate: X%
```
If no log: `Outreach: No data yet`

### Pending Replies
Check for any conversations needing response (from outreach log where status = "Replied"):
```
PENDING REPLIES: X conversations need your response
```

## Step 4: Print Status

Format the full dashboard:
```
─── ENRIQUEZ OS ───────────────────────────
EPS: [one-line from handoff] (date)
Personal: [one-line from handoff] (date)

─── PUSH ──────────────────────────────────
Intel: [freshness status]
Content buffer: [buffer status]
Outreach: [pace status]
[Pending replies if any]
[Pending inquiries if any]
────────────────────────────────────────────
```

## Step 5: Push or Ask

If there are pending replies: "You have X replies waiting. Want to handle those first?"
If content buffer is low (< 1 week): "Content buffer is low. Want to block time to batch record?"
If intel is stale: "Intel docs are stale. Want me to run a sweep?"
Otherwise: "What are we working on?"

## Rules
- Do not read CLAUDE.md files at startup — only when the task is clear
- Do not summarise handoff contents beyond the status line
- Do not read any other files until the task requires it
- Playbooks are NOT loaded at startup
- The dashboard should take < 5 seconds to generate — just file reads, no API calls
