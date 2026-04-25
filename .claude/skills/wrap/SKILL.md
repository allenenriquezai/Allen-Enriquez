---
name: wrap
description: Use when the user says "wrap", "wrap up", "done", "we're done", "that's it", "close out", "end session", "finish up", "we're good", "shutting down", "calling it", "let's stop here", "session handoff", "hand off", or any signal that the session is ending. Produces a chat handoff + learning sweep that writes to memory so the system automatically improves over time.
---

# Wrap

Two steps: (1) chat handoff for context continuity, (2) learning sweep → memory writes.

## When to invoke

User says: "session handoff", "wrap up session", "hand off", "handoff summary", "wrap", "wrap up", "let's wrap up", "summarize before I clear", or any near-equivalent.

## How to produce

1. Review the full conversation — not just recent turns.
2. Pull state from: plan files at `/Users/allenenriquez/.claude/plans/`, todos, background processes, files modified, memory files written, unresolved questions.
3. No filesystem auditing — synthesis only. No `git log`, no broad Glob sweeps.

---

## Part 1 — Chat handoff

```
# Session Handoff — <one-line title>

## Where it started
<2-3 sentences: what was asked, key constraints>

## Decisions locked + what shipped
- <decision or change> — <why, absolute path>

## Key files for next session
- `<absolute path>` — <why read first>
- Plan file: `<path>` (if a plan drove the session)
- Memory files touched: `<paths>` (if any)

## Running state
- Background processes: <shell IDs + what + kill command> — or "none"
- Dev servers / ports: <url + port> — or "none"
- Open worktrees / branches: <paths> — or "none"

## Verification — how to confirm things still work
- `<command>` — <expected outcome>

## Deferred + open questions
- Deferred: <item> — <why>
- Open: <question> — <context>

## Pick up here
<1-2 sentences: single most likely next action>
```

---

## Part 2 — Learning sweep (automatic bettering)

After the chat handoff, scan the session for insights. This is what makes the system improve without Allen having to manually say "save this."

**Priority order:** corrections first → failures → patterns → efficiency → insights

**Rules:**
- Max 2 memory writes per session
- UPDATE an existing memory file before creating a new one — check MEMORY.md index first
- Only write high-confidence observations (Allen explicitly stated it, or it fixes a known incident)
- Silent — never ask Allen to confirm

**Memory file format** (`/Users/allenenriquez/.claude/projects/-Users-allenenriquez-Developer-Allen-Enriquez/memory/`):
```markdown
---
name: <topic name>
description: <one-line — used to decide relevance in future conversations>
type: feedback | user | project | reference
---

<memory content>

**Why:** <reason Allen gave or incident that prompted this>
**How to apply:** <when/where this guidance kicks in>
```

After writing/updating a memory file, add or update its pointer in `MEMORY.md`:
```
- [Title](filename.md) — one-line hook
```

---

## Hard rules

1. Chat output first, memory writes after.
2. Never invent state — write "none" for empty sections, never omit them.
3. Absolute paths always in chat output.
4. No emojis, no hype. Terse and concrete.
5. Background process IDs must include kill commands.
6. Max 2 memory writes. Update-first. Corrections and failures only unless nothing to correct.
