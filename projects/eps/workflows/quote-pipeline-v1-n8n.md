# EPS Quote Pipeline — v1 (n8n)

Reference only. This is the old automated system built in n8n. Use this to understand what existed before rebuilding.

---

## Overview

8 n8n workflows chained via `executeWorkflow`. Entry point: a webhook on a Pipedrive deal.

```
WF-01 Intake Gate
  └── WF-02A (EPS Clean Analyzer)
        ├── WF-02.A.B (Bond Clean — Google Slides path)
        └── WF-03A (Clean Pricing Engine)
              └── WF-04 (Quote Composer)
                    └── WF-05 (Document Creation)
  └── WF-02B (EPS Paint Analyzer)
        └── WF-03B (Paint Pricing Engine)
              └── WF-04 (Quote Composer)
                    └── WF-05 (Document Creation)
```

---

## Step 1 — Intake Gate (WF-01)

Webhook receives deal ID → fetches deal + person from Pipedrive.

Security gate validates:
- `pipeline_id` / `stage_id` must be an allowed pair
  - EPS Clean: pipeline 1 / stage 24
  - EPS Paint: pipeline 2 / stage 27
- `mode` custom field must equal `CREATE V1` (field ID: `id 169`)

If valid:
- Sets `businessDivision` (Clean or Paint)
- Routes to WF-02A (Clean) or WF-02B (Paint)

If invalid: stops silently.

---

## Step 2 — AI Analyzer (WF-02A / WF-02B)

Fetches deal → reads raw quote brief from Pipedrive custom field `cb25df0d7fbc6da63daa6a50b1c161ae6579488e` (discovery notes).

Passes brief to **GPT-4.1-mini** as orchestrator with specialist sub-agent tools:

**EPS Clean (WF-02A) — 7 specialists:**
- Construction Cleaning (1-stage, 2-stage, 3-stage)
- Bond Clean
- Commercial Regular / One-Off
- Residential Regular / One-Off
- Minor Services

**EPS Paint (WF-02B) — 4 specialists:**
- Roof Painting
- External Painting
- Multiple (combined)
- Internal Painting

AI output: structured JSON with `serviceCategory`, `lineItemsForPricing`, and job metadata.

After parsing:
- Creates a team note in Pipedrive with the AI summary
- Routes: bond_clean → WF-02.A.B; everything else → WF-03A or WF-03B

---

## Step 2b — Bond Clean Path (WF-02.A.B)

Separate pathway for bond cleans only. Produces a Google Slides presentation instead of a quote spreadsheet.

Extracts: bedrooms, bathrooms, carpeted areas, window hours, storeys, extra charges.

Calculates 3 pricing packages:
- **Essential** — base scope
- **Plus** — mid tier
- **Premium** — full scope (anchor price)

Google Drive:
- Creates client folder
- Copies Google Slides template
- Replaces all placeholders with job data

Updates deal with presentation link + creates summary note in Pipedrive.

---

## Step 3 — Pricing Engine (WF-03A / WF-03B)

Applies hardcoded `PRODUCT_RATES` to `lineItemsForPricing` from the AI output.

**EPS Clean rates:**
| Code | Rate |
|------|------|
| EPSCLEAN-HOUR | $70/hr |
| EPSCLEAN-GLASS&WINDOW | $85/hr |
| EPSCLEAN-BUILD-01 | $7.50/sqm |
| EPSCLEAN-BUILD-02 | $8.25/sqm |
| EPSCLEAN-BUILD-03 | $9.00/sqm |

**EPS Paint rates:**
| Code | Rate |
|------|------|
| EPSPAINT-EXT-01 | $30/sqm (external walls) |
| EPSPAINT-EXT-03 | $20/lm (fascia/gutters) |
| EPSPAINT-EXT-05 | $500/item (garage door) |
| EPSPAINT-EXT-06 | $25/sqm (roof) |
| EPSPAINT-INT-01 | $22/sqm (internal walls) |
| EPSPAINT-INT-02 | $22/sqm (ceilings) |

If AI returns rate = 0, fallback line items were pre-configured.

Passes priced line items to WF-04.

---

## Step 4 — Quote Composer (WF-04)

Intake guard normalises fields.

Routes by `serviceCategory` via Switch node to 11 LIB nodes:
1. Construction Cleaning 1-stage
2. Construction Cleaning 2-stage
3. Construction Cleaning 3-stage
4. Bond Clean
5. Commercial Regular
6. Commercial One-Off
7. Residential Regular
8. Residential One-Off
9. Internal Painting
10. External Painting
11. Roof / Multiple Painting

Each LIB node returns a `jobDescription` boilerplate with placeholders.

**Quote Data Organiser** resolves final description by substituting:
- `[Person Name]`
- `[Project Address]`
- `[Date]`
- `[Job Summary Bullets]`
- `[Dynamic Project Details]`
- `[Specific Client Requests Block]`

**Quote Validator** checks: `finalJobDescription` + `lineItems` both present.
- Valid → WF-05
- Invalid → creates error activity in Pipedrive

---

## Step 5 — Document Creation (WF-05)

Intake Guard resolves: folder link, sheet template ID, addresses.

Google Drive folder logic:
- Empty → create new folder, update deal with link
- Existing → use it

Copies Google Sheets template named: `[serviceCategoryTitle] Quote For [personName]`

Templates:
- EPS Clean template ID (in workflow config)
- EPS Paint template ID (in workflow config)

**Line Item Mapper** normalises items.

**Build Sheet Payload** calculates row range:
- `lineStartRow`: 182
- `reservedRowCount`: 23
- If extra rows needed → `insertDimension` via Sheets batchUpdate first

**Write Sheet Data:**
- Line items (code, description, qty, unit, rate, amount)
- Org/person/address cells
- Estimate total
- Date
- Job description

**Insert Totals** writes formulas: Subtotal / GST / Total

Updates deal with spreadsheet link.

Resets `mode` field to `OFF`.

---

## Notes

- All workflows chained via `executeWorkflow` (synchronous)
- No webhooks between steps — linear chain only
- Pipedrive is source of truth: discovery notes in, doc link out
- Bond clean is the only service that produces a Slides presentation (not Sheets)
- Rate fallbacks existed for zero-rate AI responses
- Mode field acts as a run-once guard (CREATE V1 → OFF)
