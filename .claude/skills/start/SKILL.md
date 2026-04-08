---
name: start
description: Use at the beginning of each session to load minimal context and resume from last handoff.
disable-model-invocation: true
---

Start the session lean — load only what's needed, nothing more.

1. Read ALL handoff files (Allen runs parallel sessions, so any project may have changed):
   - `projects/eps/.tmp/session_handoff.md`
   - `projects/personal/.tmp/session_handoff.md`
   - `projects/executive-assistant/.tmp/session_handoff.md`
   Skip any that don't exist. Do not error.

2. Print a 2-3 line status across all projects that have handoffs. Format:
   ```
   EPS: [one-line summary from handoff] (date)
   Personal: [one-line summary from handoff] (date)
   EA: [one-line summary from handoff] (date)
   ```
   Only show projects that have a handoff file.

3. Ask: "What are we working on?"

Do not read CLAUDE.md files at startup — only read them once the task is clear.
Do not summarise handoff contents beyond the status line.
Do not read any other files until the task requires it.
