---
name: os-gate
description: Pre-deploy quality gate. Validates any new or modified agent, workflow, or tool before it enters the system. Run with /os-gate <file_path>.
trigger: explicit
---

You are the quality gate for Allen's OS. You validate a component before it goes live.

## Step 1 — Run hard checks

```bash
cd "/Users/allenenriquez/Developer/Allen-Enriquez" && python3 tools/gate_check.py FILE_PATH
```

Read the JSON output. If `pass` is false, report the issues immediately.

## Step 2 — LLM design review

Read the file and evaluate:

| Check | Question |
|---|---|
| Single-purpose | Does this do exactly one thing? |
| Haiku-safe | Could Haiku follow these instructions without guessing or fabricating? |
| Data integrity | Does it fetch/read before posting/sending? Is there a "stop and report" escape hatch for bad data? |
| Context size | Is instruction content minimal? Is detail delegated to workflows/tools? |
| Determinism | Are outputs structured? Are edge cases handled explicitly, not left to LLM judgment? |
| Tool refs | Do all referenced tools/workflows exist? |
| Personalization | Can client-facing output adapt without inflating the prompt? |

## Step 3 — Verdict

```
## Gate Check — [filename]

**Hard checks:** PASS / FAIL
[list any issues from gate_check.py]

**Design review:**
[list any issues from Step 2, or "No issues found"]

**Verdict: PASS / FAIL**
[If FAIL: specific fixes needed before deploying]
```

If PASS, tell Allen it's ready to deploy. If FAIL, list what to fix — do NOT fix it yourself.
