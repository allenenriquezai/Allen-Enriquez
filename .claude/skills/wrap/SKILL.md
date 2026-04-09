---
name: wrap
description: Use at the end of a session to save a compact handoff note and log decisions so the next session can resume with full context.
disable-model-invocation: true
---

Save a handoff note + decision log entry so the next session understands what was done and why.

## Step 1 — Session handoff

Identify which project was active (eps / personal / both). Write `projects/[project]/.tmp/session_handoff.md`:

```
## Handoff — [YYYY-MM-DD]
**Done:** 
- [file path changed or created]

**Decisions:**
- [key choice and why]

**Next:**
- [explicit next step]

**Blockers:**
- [open question or blocker, or "none"]
```

If multiple projects were touched, write one file per project.

## Step 2 — Decision log (only if system was modified)

If this session changed any agent, skill, tool, workflow, or automation file, append an entry to `DECISIONS.md` at project root:

```
## YYYY-MM-DD — [Short title]
**Problem:** What was wrong or missing
**Change:** What was done (files changed)
**Why:** Reasoning — what alternatives were considered and why this was chosen
**Criteria:** Speed: [+/-/=] | Cost: [+/-/=] | Accuracy: [+/-/=] | Scale: [+/-/=]
**Next:** What could improve from here
```

Skip this step if the session was only reading/researching/discussing — no system changes.

## Rules
- Use the Write tool for handoffs, Edit tool (append) for DECISIONS.md
- Overwrite any existing handoff file at that path
- Bullet points only, no prose
- Criteria uses the 4 design principles from CLAUDE.md: Speed, Cost, Accuracy, Scale
- Mark each as + (improved), - (regressed), or = (no change)
