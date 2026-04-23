
# EPS Deposit Skill

Run the deposit process after a client accepts a quote. Pushes job to ServiceM8, records deposit, then Allen sends the invoice manually from the SM8 UI.

---

## Overview

```
Client accepts quote
    -> Pipedrive automation: deal -> SITE VISIT + creates SM8 job card
    -> Run: push_sm8_job.py  (migrate description + line items -> SM8)
    -> Deal auto-moves to: DEPOSIT PROCESS
    -> Run: create_sm8_deposit.py  (calculates deposit amount)
    -> Manually: SM8 UI -> Billing -> Send Quote -> Partial Invoice -> set amount -> Send
```

---

## Domain Knowledge

### Pipeline + Stage IDs

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
- `PIPEDRIVE_API_KEY`
- `PIPEDRIVE_COMPANY_DOMAIN`
- `PIPEDRIVE_FOLDER_FIELD_KEY` — required by `update_pipedrive_deal.py`; if missing, doc/folder links silently fail
- `PIPEDRIVE_DOC_FIELD_KEY` — same

All in `projects/eps/.env`.

---

## Decision Logic

| Situation | Action |
|---|---|
| `projects/eps/.tmp/quote_data.json` exists | Proceed — data is ready |
| `.tmp/quote_data.json` missing (cold session) | **Stop.** Re-run `/eps-quote` for this deal first to rebuild the file, then return here |
| SM8 job # field is empty on the Pipedrive deal | **Stop.** Tell Allen: "Move the deal to SITE VISIT in Pipedrive and wait for the automation to fire, then re-run this." |
| SM8 API key missing from `.env` | **Stop.** Tell Allen which key is missing and where to add it |
| Custom deposit % requested | Pass `--pct X` to create_sm8_deposit.py |
| Wrong pipeline (not 1 or 2) | **Stop.** This process only applies to EPS Clean and EPS Paint |

---

## Step 1 — Verify Deal is Ready

Fetch the deal from Pipedrive. Confirm:
- SM8 job # field is populated
- Pipeline is 1 (EPS Clean) or 2 (EPS Paint)
- `quote_data.json` exists in `.tmp/`

---

## Step 2 — Push Job Description + Line Items to SM8

```bash
python3 tools/eps/push_sm8_job.py --deal-id <deal_id>
```

What it does:
- Reads `quote_data.json` from `.tmp/`
- Fetches deal from Pipedrive -> gets SM8 job # (e.g. #EPS-6383)
- Looks up the SM8 job by that number
- Pushes job description to SM8
- Creates line items (JobMaterials) in SM8
- Moves Pipedrive deal to DEPOSIT PROCESS stage
- Saves `sm8_data.json` to `.tmp/`

Guard: Only runs on Pipeline 1 (EPS Clean) or Pipeline 2 (EPS Paint).

---

## Step 3 — Calculate Deposit Amount

```bash
python3 tools/eps/create_sm8_deposit.py --deal-id <deal_id>
# or with custom %:
python3 tools/eps/create_sm8_deposit.py --deal-id <deal_id> --pct 30
# or with fixed amount:
python3 tools/eps/create_sm8_deposit.py --deal-id <deal_id> --amount 500
```

Default deposit: **50% of quote total (inc GST)**

What it does:
- Reads `sm8_data.json` (+ `quote_data.json` if using `--pct`) from `.tmp/`
- Calculates and prints the deposit amount
- Prints SM8 UI instructions

---

## Step 4 — Create Partial Invoice (SM8 UI — Manual)

SM8's REST API does not support creating invoices. Do this in SM8:

1. Open SM8 -> find job (e.g. #EPS-6383)
2. **Billing -> Send Quote -> Partial Invoice**
3. Set amount to the deposit amount from Step 3
4. Send to client — SM8 creates a sub-job (e.g. EPS-6383A)

Tell Allen: "Open SM8 -> find job [#EPS-XXXX] -> Invoices -> New Partial Invoice -> set amount to $[deposit amount] -> send to client."

---

## Key Pipedrive Fields

| Field | Key |
|---|---|
| Sm8 Job # | `052a8b8271d035ca4780f8ae06cd7b5370df544c` |
| Quote Folder Link | `04ed807860923fac89bedf563b1c5409e1f9e862` |
| Draft Quote Doc | `c031a16cda356f6371b724d40b4c8f7ddbb4e094` |

---

## Temp Files

| File | Source | Used by |
|---|---|---|
| `projects/eps/.tmp/quote_data.json` | eps-quote skill | push_sm8_job.py, create_sm8_deposit.py |
| `projects/eps/.tmp/sm8_data.json` | push_sm8_job.py | create_sm8_deposit.py |

---

## Success Criteria

- SM8 job has job description + line items pushed
- Pipedrive deal moved to DEPOSIT PROCESS
- Deposit amount printed and confirmed
- Allen has the SM8 job number and deposit amount to send the invoice manually

---

## Troubleshooting

**"Sm8 Job # field is empty"**
-> The Pipedrive automation hasn't run yet. Move the deal to SITE VISIT first and wait for automation to fire.

**"No SM8 job found with generated_job_id"**
-> The SM8 job number in Pipedrive doesn't match what's in SM8. Check the SM8 job # field on the deal.

**SM8 API key error**
-> Add `SM8_API_KEY_CLEAN` or `SM8_API_KEY_PAINT` to `projects/eps/.env`.
