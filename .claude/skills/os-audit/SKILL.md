---
name: os-audit
description: Audit context bloat — agents, skills, memory. Run with /os-audit to check what's eating session tokens.
---

Context bloat auditor. Checks what auto-loads into every session and flags problems.

## What to check

Run these bash commands and collect results:

```bash
# 1. Registered agents (should be 0 — agents live in projects/*/agents/)
ls -1 .claude/agents/ 2>/dev/null | wc -l

# 2. Skill count and sizes
wc -c .claude/skills/*/SKILL.md 2>/dev/null; wc -c .claude/skills/*/skill.md 2>/dev/null

# 3. Memory file count and total size
ls -1 ~/.claude/projects/-Users-allenenriquez-Desktop-Allen-Enriquez/memory/*.md 2>/dev/null | grep -v MEMORY.md | wc -l
wc -c ~/.claude/projects/-Users-allenenriquez-Desktop-Allen-Enriquez/memory/*.md 2>/dev/null | tail -1

# 4. CLAUDE.md sizes
wc -c CLAUDE.md projects/*/CLAUDE.md 2>/dev/null
```

## Thresholds

| Check | Green | Yellow | Red |
|---|---|---|---|
| Agents in `.claude/agents/` | 0 | 1-3 | 4+ |
| Skill count | ≤15 | 16-20 | 21+ |
| Any single skill file | ≤2KB | 2-4KB | 5KB+ |
| Total skill size | ≤25KB | 25-40KB | 40KB+ |
| Memory file count | ≤20 | 21-30 | 31+ |
| Total memory size | ≤30KB | 30-50KB | 50KB+ |
| Any CLAUDE.md file | ≤5KB | 5-8KB | 8KB+ |
| Any playbook file | ≤2KB | 2-3KB | 3KB+ |

## Output format

Print a table with current values and status (green/yellow/red). Flag any red items with a recommended fix.

Example:
```
## Context Audit

| Check                  | Value  | Status |
|------------------------|--------|--------|
| Registered agents      | 0      | green  |
| Skills                 | 14     | green  |
| Largest skill          | 4.9KB  | yellow |
| Total skill size       | 22KB   | green  |
| Memory files           | 18     | green  |
| Total memory size      | 28KB   | green  |
| Main CLAUDE.md         | 4.3KB  | green  |

No red flags.
```

If any red items found, list specific recommendations (e.g. "find-skills SKILL.md is 4.9KB — trim or delete").
