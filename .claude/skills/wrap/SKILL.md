---
name: wrap
description: Use at the end of a session to save a compact handoff note so the next session can resume without re-reading everything.
disable-model-invocation: true
---

Save a compact handoff note using the Write tool so the next session can resume without re-reading everything.

Steps:
1. Identify which project was active this session (eps / personal-brand / personal)
2. Use the Write tool to create `projects/[project]/.tmp/session_handoff.md` with this format:

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

3. Print: "Handoff saved to projects/[project]/.tmp/session_handoff.md"

Rules:
- Use the Write tool — do not just print the content
- Overwrite any existing file at that path
- Bullet points only, no prose
- If multiple projects were touched, write one file per project
