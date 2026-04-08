---
name: os-review
description: Full system audit — scans skills, agents, workflows, Gmail (EPS + personal), Calendar, and Pipedrive to find what to improve or build next. Report only, no changes made.
trigger: explicit
---

You are running a full audit of Allen's personal OS. Your job is to produce a structured findings report. You make ZERO changes — report only. Allen will decide what to act on.

## Step 1 — Fetch live data

Run this first:
```bash
cd "/Users/allenenriquez/Desktop/Allen Enriquez" && python3 tools/fetch_review_data.py
```

If it fails partially (e.g. personal Gmail not set up yet), continue — just note which sources were skipped.

## Step 2 — Read all local files

Read these in parallel:
- All files in `.claude/skills/*/SKILL.md`
- All files in `.claude/agents/*.md`
- All files in `projects/eps/workflows/*.md`
- All files in `.claude/projects/-Users-allenenriquez-Desktop-Allen-Enriquez/memory/`
- File list only (no content) for `tools/`

## Step 3 — Read the fetched data

Read `.tmp/review_data.json` — this contains Gmail threads, Calendar events, and Pipedrive notes/activities from the last 30 days.

## Step 4 — Analyse

Cross-reference everything. Look for:

**Integrity (run first):**
- Any agent over 150 lines or workflow over 200 lines → flag for splitting
- Any `tools/*.py` referenced in agents/workflows that doesn't exist → flag
- Tools in `tools/` not referenced by any agent, workflow, or skill → flag as orphan
- Review `projects/eps/reference/incident-log.md` for recurring patterns

**Improve:**
- Existing skills with missing steps, wrong triggers, or outdated instructions
- Agents with gaps vs the workflows they're supposed to serve
- Memory entries that are stale or contradicted by current code

**Build:**
- Workflows or repeating Pipedrive patterns that have no skill yet
- Tools in `tools/` that have no corresponding workflow or skill
- Patterns in emails/calendar that indicate a recurring task with no automation

**Remove:**
- Duplicate skills or workflows
- Memory entries that are no longer relevant
- Dead tools (not referenced anywhere)

## Step 5 — Output

Produce a findings report in this exact format:

---

## OS Review — [today's date]

**Sources scanned:** [list which sources had data vs were skipped]

### Findings

| # | Item | Type | Finding | Suggested Action |
|---|---|---|---|---|
| 1 | ... | Improve/Build/Remove | ... | ... |
...

_(max 10 rows)_

### Top 3 to act on now
1. **[Item]** — [one sentence why this is highest priority]
2. **[Item]** — ...
3. **[Item]** — ...

---

Then stop. Ask Allen: "Which of these do you want to work on?"

Do NOT make any changes to any files until Allen tells you what to act on.
