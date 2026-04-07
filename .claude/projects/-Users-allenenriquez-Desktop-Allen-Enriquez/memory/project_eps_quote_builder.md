---
name: EPS Quote Builder — Current State
description: Progress and decisions on the EPS automated quote builder pipeline
type: project
---

Quote builder pipeline is complete through Stage 5. Last updated 2026-04-07.

## Full Pipeline

```
Stage 0: Collect service type + client context → write job_description into quote_data.json
Stage 1: Intake (client, address, job type, floor plan or text scope, deal ID)
Stage 1b: Rate selection (default / multiplier / custom)
Stage 2: Measure (floor plan → rooms.json) or skip if text scope
Stage 3: calculate_quote.py → quote_data.json (painting only)
         For cleaning: write quote_data.json manually (calculator doesn't support cleaning tokens yet)
Stage 3b: Custom line items — write quote_data.json directly for lump-sum or cleaning jobs
Stage 4: create_quote_folder.py → fill_quote_template.py → export_quote_pdf.py
Stage 4b: update_pipedrive_deal.py (requires PIPEDRIVE_DRIVE_FIELD_KEY in .env)
Stage 5: qa_quote.py — checks quote + posts QA report + email draft as pinned note on Pipedrive deal
Stage 5b: draft_quote_email.py --send — sends after Allen approves in Pipedrive
```

## Scripts (all in tools/)

- `calculate_quote.py` — painting only. Cleaning line items must be written manually.
- `create_quote_folder.py` — creates Drive subfolder, copies Doc template
- `fill_quote_template.py` — fills placeholders + line items table in Google Doc
- `export_quote_pdf.py` — exports Google Doc → `.tmp/quote_output.pdf`
- `update_pipedrive_deal.py` — writes doc URL to deal custom field (needs PIPEDRIVE_DRIVE_FIELD_KEY)
- `qa_quote.py` — QA checks + posts email draft as pinned Pipedrive note for approval
- `draft_quote_email.py` — drafts email from template + sends via Pipedrive API
- `send_email_pipedrive.py` — low-level email sender (imported by draft_quote_email.py)

## Email Templates

`projects/eps/templates/email/quotes/` — one file per service type:
- `residential_painting.txt` — emotional tone, concern-led. All 4 reference links embedded.
- `residential_cleaning.txt` — personal tone. EPS Clean site, Facebook, Instagram.
- `builders_cleaning.txt` — professional, proof-led. YouTube, Instagram, epsclean projects, site.
- `builders_painting.txt` — professional. YouTube, Drive references, Instagram, epspaint site.
- `builders_painting_cleaning.txt` — both services combined.
- `bond_clean.txt` — references in quote doc itself.

Folder structure also has: `follow_ups/`, `bookings/`, `support/` (empty, for future use).

## QA Agent (qa_quote.py)

Checks: required fields, job description sections, line item math, no unfilled placeholders, word count.
On pass: posts QA report + email draft as pinned note on Pipedrive deal.
Allen reviews in Pipedrive → approves → run draft_quote_email.py --send.

## Key Decisions

- **Google Docs over Sheets** — Docs PDF export is clean. Sheets is fragile.
- **Line items per component** — split by townhouse/unit/level, not aggregate totals.
- **Job description** — must follow full structured format from `job_descriptions/<service>.md` (all sections).
- **Cleaning calculator gap** — `calculate_quote.py` only handles painting scope tokens. Cleaning line items written manually until cleaning tokens are added.
- **Email via Pipedrive API** — NOT Gmail. References are hyperlinked in HTML.
- **QA gate before send** — qa_quote.py must pass before draft_quote_email.py --send.
- **Mob fee optional and variable** — pass --mob AMOUNT to include.

## Config (projects/eps/config/pricing.json)

- `eps_quotes_folder_id`: `1Z-GLrFw4K5qmpKDsbKbWqg7PLQYUX9vl`
- `templates.paint` (Doc): `1oR4r7O6LELEyYEXlYq3iQyTlXDhH5Lf1RwPaGIP7aqg`
- `templates.clean` (Doc): `1OEjAWR_UBzs1xmcWCvDIFoBpcC06ggBFEswyPfqN4DY`

Cleaning rates: Stage 1 $7.50/sqm, Stage 2 $8.25/sqm, Stage 3 $9.00/sqm, Window $85/hr.

## What's Next

- Add cleaning scope tokens to `calculate_quote.py` so cleaning quotes can be automated
- `PIPEDRIVE_DRIVE_FIELD_KEY` not yet set in .env — `update_pipedrive_deal.py` won't work until filled
- Email scope bullets in QA/draft show per-unit line items (too granular) — need a summary mode
- More email templates to add: cold emails, follow-ups, booking confirmations, support responses
