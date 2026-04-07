---
name: start
description: Use at the beginning of each session to load minimal context and resume from last handoff.
disable-model-invocation: true
---

Start the session lean — load only what's needed, nothing more.

1. Ask: "Which project? (eps / personal-brand / personal)" — skip if already obvious from context
2. Check if `projects/[project]/.tmp/session_handoff.md` exists
   - If yes: read it, then say in one line what state we're resuming from
   - If no: read `projects/[project]/CLAUDE.md` only
3. Ask: "What are we working on?"

Do not read any other files until the task requires it.
Do not summarise the CLAUDE.md back to the user.
