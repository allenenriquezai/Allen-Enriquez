---
name: eps-quote
description: Use when generating a quote for an EPS Painting & Cleaning client. Triggered when someone asks to create, build, or generate a quote for a job.
disable-model-invocation: true
---

# EPS Quote Skill

Spawn the **eps-quote-agent** to handle this end-to-end. Pass all context Allen provided (deal ID, client name, scope, floor plan path, rates).

---

## Domain Knowledge

### Service types
- **Painting:** internal_painting, external_painting, roof_painting, multiple_painting, deck_stain_or_paint, commercial_painting, hourly_painting, day_rate_painting, misc_painting_repairs
- **Cleaning:** construction_cleaning_1_stage, construction_cleaning_2_stage, construction_cleaning_3_stage, bond_clean, commercial_regular_cleaning, commercial_oneoff_cleaning, residential_regular_cleaning, residential_oneoff_cleaning, window_glass_cleaning, carpet_steam_cleaning, pressure_cleaning

### Two calculators — do not mix them
- **Painting** → `calculate_quote.py` (scope-based, per-sqm rates)
- **Cleaning** → write `quote_data.json` manually (no calculator — lump sum or sqm × rate)

### Job descriptions come from templates — never rewrite
- Source: `projects/eps/job_descriptions/<service_type>.md`
- Copy verbatim. Only fill `[placeholders]` with client context.
- Each top-level section = one string in the `job_description` array
- Multi-stage cleans: Stage sub-sections nest inside SCOPE OF WORK — not separate items

### Rates
- Config: `projects/eps/config/pricing.json`
- Ask Allen for rate preference (default / multiplier / custom) before calculating
- Mob fee ($100) is optional and variable — ask if it applies

---

## Decision Logic

| Situation | Action |
|---|---|
| Floor plan provided | Run eps-measure first → rooms.json → then line items |
| Text scope only | Skip measurement → pass scope directly to calculate_quote.py |
| Painting job | Use calculate_quote.py with aggregate scope string |
| Cleaning job | Write quote_data.json manually (per pricing.json clean rates) |
| Deal ID provided | Fetch deal from Pipedrive first → get real client name + address |
| No deal ID | Proceed without Pipedrive — use Allen's input directly |
| Multiple service types | Build separate job descriptions → merge SCOPE OF WORK only |
| Stairwell / vaulted ceiling flagged | Offer day rate option ($1,300/painter/day) instead of sqm rates |

---

## Pipeline (Summary)

1. Collect service type + client context → write job description from template
2. Intake: client name, address, job type, floor plan or text scope, deal ID
3. Ask rates (default / multiplier / custom)
4. Measure (if floor plan) → `rooms.json`
5. Calculate line items → `quote_data.json`
6. Before QA: ensure `quote_data.json` includes `"quote_title"` — read the `<!-- quote_title: ... -->` comment from `job_descriptions/<service_type>.md`. Required by `create_sm8_deposit.py` — missing = crash.
7. Pre-doc QA: `python3 tools/qa_quote.py --data-only` — **do not proceed if FAILED**
7. Create Google Doc: `get_deal_folder.py` → `create_quote_folder.py` → `fill_quote_template.py` → `export_quote_pdf.py`
8. Write doc URL + folder URL to Pipedrive: `update_pipedrive_deal.py --field doc|folder`
9. Hand off to eps-email-agent for the quote email (Stage 5). For residential templates, ensure concern-1 and concern-2 have been collected from Allen before handing off.

---

## Tools

| Tool | Purpose |
|---|---|
| `tools/calculate_quote.py --client --address --job-type --scope [--mob] [--date]` | Painting line items — single property |
| `tools/calculate_quote.py --client --address --job-type --components components.json [--mob]` | Painting line items — multi-unit (per townhouse/level/building) |
| `tools/fill_quote_template.py --doc-id --data projects/eps/.tmp/quote_data.json` | Fill Google Doc |
| `tools/export_quote_pdf.py --doc-id` | Export PDF to `.tmp/quote_output.pdf` |
| `tools/get_deal_folder.py --deal-id` | Check for existing Drive folder |
| `tools/create_quote_folder.py --deal-id --service-type --client --division paint\|clean [--folder-id]` | Create/reuse folder |
| `tools/update_pipedrive_deal.py --deal-id --field doc\|folder --url` | Write links to Pipedrive |
| `tools/qa_quote.py --data-only` | Pre-doc validation gate |

---

## Temp Files

| File | Contains |
|---|---|
| `projects/eps/.tmp/rooms.json` | Room measurements from floor plan |
| `projects/eps/.tmp/quote_data.json` | Full quote data (client, line items, totals, job description) |
| `projects/eps/.tmp/quote_output.pdf` | Exported PDF |

---

## Success Criteria

Return to Allen:
- Google Doc URL
- Total: $X,XXX inc GST
- Any flags (estimated dimensions, stairwells, missing address, etc.)

Do not show the email draft here — that is eps-email-agent's job.

---

## Full workflow reference
`projects/eps/workflows/create-quote.md`
