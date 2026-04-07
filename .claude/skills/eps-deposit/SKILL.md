---
name: eps-deposit
description: Use when a client has accepted a quote and we need to push the job to ServiceM8 and create a deposit invoice. Triggered by phrases like "deposit process", "client accepted", "move to deposit", "push to SM8", "create deposit invoice".
disable-model-invocation: true
---

# EPS Deposit Skill

Run the deposit process after a client accepts a quote. Pushes job to ServiceM8, records deposit, then Allen sends the invoice manually from the SM8 UI.

---

## Domain Knowledge

### What triggers this
Client accepts the quote → Pipedrive automation fires → deal moves to SITE VISIT + SM8 job card is created. Then this process runs.

### Pipeline + stage IDs
| Pipeline | Account | SITE VISIT | DEPOSIT PROCESS |
|---|---|---|---|
| 1 | EPS Clean | 3 | 47 |
| 2 | EPS Paint | 10 | 48 |

### SM8 job number
Lives in Pipedrive custom field key: `052a8b8271d035ca4780f8ae06cd7b5370df544c`

### Default deposit
50% of quote total (inc GST). Can vary — ask Allen if a different % applies.

### Step 4 is always manual
SM8's API does not expose invoice generation. Allen must send the deposit invoice from the SM8 UI after the scripts run.

### Env vars required
- `SM8_API_KEY_CLEAN` — EPS Clean SM8 API key
- `SM8_API_KEY_PAINT` — EPS Paint SM8 API key
Both in `projects/eps/.env`.

---

## Decision Logic

| Situation | Action |
|---|---|
| `projects/eps/.tmp/quote_data.json` exists | Proceed — data is ready |
| `.tmp/quote_data.json` missing (cold session) | **Stop.** Re-run `/eps-quote` for this deal first to rebuild the file, then return here |
| SM8 job # field is empty on the Pipedrive deal | **Stop.** Tell Allen: "Move the deal to SITE VISIT in Pipedrive and wait for the automation to fire, then re-run this." |
| SM8 API key missing from `.env` | **Stop.** Tell Allen which key is missing and where to add it |
| Custom deposit % requested | Pass `--pct X` to create_sm8_deposit.py |
| Wrong pipeline (not 1 or 2) | **Stop.** This workflow only applies to EPS Clean and EPS Paint |

---

## Steps

### Step 1 — Verify deal is ready
Fetch the deal from Pipedrive. Confirm:
- SM8 job # field is populated
- Pipeline is 1 (EPS Clean) or 2 (EPS Paint)
- `quote_data.json` exists in `.tmp/`

### Step 2 — Push job to SM8
```bash
python3 tools/push_sm8_job.py --deal-id <deal_id>
```
What it does: reads `quote_data.json` + Pipedrive deal → finds SM8 job → pushes job description + line items → moves deal to DEPOSIT PROCESS → saves `sm8_data.json` to `.tmp/`

### Step 3 — Record deposit
```bash
python3 tools/create_sm8_deposit.py --deal-id <deal_id>
# or custom %:
python3 tools/create_sm8_deposit.py --deal-id <deal_id> --pct 30
```
What it does: reads `sm8_data.json` + `quote_data.json` → calculates deposit → records payment in SM8 → prints deposit amount.

### Step 4 — Manual (Allen)
Tell Allen: "Open SM8 → find job [#EPS-XXXX] → Invoices → New Partial Invoice → set amount to $[deposit amount] → send to client."

---

## Temp Files

| File | Source | Used by |
|---|---|---|
| `projects/eps/.tmp/quote_data.json` | eps-quote-agent | push_sm8_job.py, create_sm8_deposit.py |
| `projects/eps/.tmp/sm8_data.json` | push_sm8_job.py | create_sm8_deposit.py |

---

## Success Criteria

- SM8 job has job description + line items pushed
- Pipedrive deal moved to DEPOSIT PROCESS
- Deposit amount printed and confirmed
- Allen has the SM8 job number and deposit amount to send the invoice manually

---

## Full workflow reference
`projects/eps/workflows/deposit-process.md`
