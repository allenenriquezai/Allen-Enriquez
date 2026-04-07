# Deposit Process Workflow

Triggered when a client accepts the quote and the deal moves to SITE VISIT.

## Overview

```
Client accepts quote
    → Pipedrive automation: deal → SITE VISIT + creates SM8 job card
    → Run: push_sm8_job.py  (migrate description + line items → SM8)
    → Deal auto-moves to: DEPOSIT PROCESS
    → Run: create_sm8_deposit.py  (record 50% deposit in SM8)
    → Manually: send deposit invoice from SM8 UI
```

---

## Stage IDs

| Pipeline | Account   | SITE VISIT | DEPOSIT PROCESS |
|----------|-----------|------------|-----------------|
| 1        | EPS Clean | 3          | 47              |
| 2        | EPS Paint | 10         | 48              |

---

## Step 1 — Verify Quote Data is Ready

Make sure `projects/eps/.tmp/quote_data.json` is current for this deal.
If the quote was done in a previous session, re-run the quote pipeline first.

---

## Step 2 — Push Job Description + Line Items to SM8

```bash
python tools/push_sm8_job.py --deal-id <deal_id>
```

**What it does:**
- Reads `quote_data.json` from `.tmp/`
- Fetches deal from Pipedrive → gets SM8 job # (e.g. #EPS-6383)
- Looks up the SM8 job by that number
- Pushes job description to SM8
- Creates line items (JobMaterials) in SM8
- Moves Pipedrive deal to DEPOSIT PROCESS stage
- Saves `sm8_data.json` to `.tmp/`

**Guard:** Only runs on Pipeline 1 (EPS Clean) or Pipeline 2 (EPS Paint).

---

## Step 3 — Record Deposit in SM8

```bash
python tools/create_sm8_deposit.py --deal-id <deal_id>
# or with custom %:
python tools/create_sm8_deposit.py --deal-id <deal_id> --pct 30
```

Default deposit: **50% of quote total (inc GST)**

**What it does:**
- Reads `sm8_data.json` + `quote_data.json` from `.tmp/`
- Calculates deposit amount
- Records a payment against the SM8 job (JobPayment endpoint)
- Prints the deposit amount

---

## Step 4 — Send Deposit Invoice (Manual — SM8 UI)

SM8's REST API does not expose invoice generation directly.
Send the deposit invoice from the SM8 app:

1. Open SM8 → find job (e.g. #EPS-6383)
2. Go to **Invoices** → **New Partial Invoice**
3. Set amount to the deposit amount shown by the script
4. Send to client from SM8

---

## Env Vars Required

```
SM8_API_KEY_CLEAN=<EPS Clean SM8 API key>
SM8_API_KEY_PAINT=<EPS Paint SM8 API key>
PIPEDRIVE_API_KEY=<Pipedrive API key>
PIPEDRIVE_COMPANY_DOMAIN=<e.g. essentialpropertysolutionsptyltd.pipedrive.com>
PIPEDRIVE_FOLDER_FIELD_KEY=<hash for Quote Folder Link field>
PIPEDRIVE_DOC_FIELD_KEY=<hash for Draft Quote Doc Link field>
```

Add to `projects/eps/.env`. `PIPEDRIVE_FOLDER_FIELD_KEY` and `PIPEDRIVE_DOC_FIELD_KEY` are required by `update_pipedrive_deal.py` — if missing, doc/folder links will silently fail to write to Pipedrive.

---

## Key Pipedrive Fields

| Field             | Key                                              |
|-------------------|--------------------------------------------------|
| Sm8 Job #         | `052a8b8271d035ca4780f8ae06cd7b5370df544c`       |
| Quote Folder Link | `04ed807860923fac89bedf563b1c5409e1f9e862`       |
| Draft Quote Doc   | `c031a16cda356f6371b724d40b4c8f7ddbb4e094`       |

---

## Troubleshooting

**"Sm8 Job # field is empty"**
→ The Pipedrive automation hasn't run yet. Move the deal to SITE VISIT first and wait for automation to fire.

**"No SM8 job found with generated_job_id"**
→ The SM8 job number in Pipedrive doesn't match what's in SM8. Check the SM8 job # field on the deal.

**SM8 API key error**
→ Add `SM8_API_KEY_CLEAN` or `SM8_API_KEY_PAINT` to `projects/eps/.env`.
