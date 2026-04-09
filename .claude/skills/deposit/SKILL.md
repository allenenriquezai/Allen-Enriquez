---
name: deposit
description: Push job description + line items to ServiceM8 after a client accepts a quote. Triggers on "run the deposit", "process the deposit", "client accepted", "push to SM8", or /deposit.
---

EPS deposit process. Do NOT read any other files — everything you need is here.

## Inputs
- **Deal ID** (required)

## Prerequisites — check before running

1. `projects/eps/.tmp/quote_data.json` must exist. If missing: STOP — run `/quote` for this deal first.
2. SM8 Job # must be populated on the Pipedrive deal. If missing: STOP — tell Allen to move the deal to SITE VISIT in Pipedrive and wait for the automation to fire.
3. Deal must be in Pipeline 1 (EPS Clean) or Pipeline 2 (EPS Paint). If not: STOP.
4. SM8 API keys must exist in `projects/eps/.env` (`SM8_API_KEY_CLEAN` or `SM8_API_KEY_PAINT`). If missing: STOP — tell Allen which key to add.

## Steps

### Step 1 — Push job to ServiceM8
```bash
python3 tools/push_sm8_job.py --deal-id DEAL_ID
```
Pushes job description + line items from quote_data.json to SM8. Moves deal to DEPOSIT PROCESS stage.

Report to Allen: SM8 job number, what was pushed, and confirm deal stage moved.

## Rules
- Do NOT read workflow files or memory — just run the step above
- Always load credentials from `projects/eps/.env`
- For detailed troubleshooting, see `projects/eps/workflows/deposit-process.md`
