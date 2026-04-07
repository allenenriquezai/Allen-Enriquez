---
name: EPS Quoting System — build status
description: Status of the EPS painting & cleaning quote automation system being built in projects/eps/
type: project
---

Building an automated quoting system for EPS Painting & Cleaning (Brisbane). Allen is sales manager, closing ~$100K/month. **Two sister companies: EPS Painting and EPS Cleaning — quote builder should work for both.**

## What's built

- `/eps-measure` skill → `workflows/measure-floor-plan.md` — extracts room dimensions from floor plan via Claude vision
- `/eps-lineitems` skill → `workflows/calculate-line-items.md` — generates priced line items from room data
- `/eps-quote` skill → `workflows/create-quote.md` — full pipeline (intake → measure → line items → Google Doc → Pipedrive)
- `tools/create_quote_folder.py` — creates Google Drive folder + copies quote template
- `tools/fill_quote_template.py` — fills `{{PLACEHOLDER}}` tags in Google Doc
- `tools/update_pipedrive_deal.py` — writes doc URL to Pipedrive deal custom field
- `projects/eps/config/pricing.json` — full EPS rate schedule (INT-01 through EXT-06, all rates populated)
- `projects/eps/config/products.json` — full product list with codes, names, unit prices, units (sqm/lm/item/door)
- `projects/eps/.tmp/rooms.json` — test output from Formosa Rd floor plan (includes Togal measurements)

## Products (from products.json)

Unit types used:
- `sqm` — INT-01 walls ($22), INT-02 ceilings ($22), INT-06 patch ($12), INT-07 feature wall ($28), EXT-01 low ($22), EXT-02 high ($30), EXT-04 deck ($50), EXT-06 roof ($25)
- `lm` — INT-04 skirting ($10), INT-05 architraves ($9), EXT-03 fascia/eaves/gutter ($20)
- `door` — INT-03 internal door both sides ($150)
- `item` — EXT-05 garage door ($500), EPSMOB mobilisation ($100), EPSPAINT-DAYRATE ($1300/day), EPSPAINT-HR ($160/hr)

**Pricing logic: NOT YET CONFIRMED.** Allen got cut off when explaining "we price them like: per floor..." — need to clarify:
- INT-01/02: total area flat, or broken out per room on the quote?
- INT-04/05 (skirting/architraves): unit is lm confirmed, but how is lm calculated from plan?
- INT-03 (doors): counted from plan or client-supplied?

## Measurement accuracy (tested on 2 Formosa Rd, Belmont)

| Path | Accuracy | Status |
|------|----------|--------|
| Vision only | ~87% | Working now |
| Vision + Togal aggregates | ~92% | Working now |
| Manual Togal export | ~98% | Can do anytime — Allen to export room CSV |
| Togal API (per-room) | ~98% | Pending — Allen contacting Togal support |

**Togal figures for Formosa Rd test:**
- Wall perimeter: 408.29 lm → wall area = 1,118.7 m²
- Net area: 415.76 m² (33 rooms)
- Gross interior: 381.67 m² → use for ceiling area
- Doors: 22

**Key insight:** Vision was 13% low on wall area (973 vs 1,119 m²) — would have underpriced the job. Togal aggregates must be used as anchor figures.

## Blockers before first live test

1. **Google Doc template ID** — Allen to share link → set `template_doc_id` in `pricing.json`
2. **Pipedrive API key + custom field key** → `PIPEDRIVE_API_KEY` and `PIPEDRIVE_DRIVE_FIELD_KEY` in `projects/eps/.env`
3. **Pricing logic confirmation** — how line items are structured on the quote (Allen got cut off)
4. **Togal API** — pending support response; manual export is fallback

## EPS Clean extension

Allen wants the quote builder to work for EPS Cleaning as well (sister company, same structure). Allen has an EPS Clean workflow — ask him to re-share if needed. Architecture should support both companies via a `company` param or separate config/products files.

## Phase 2 (not started)

Trigger.dev agent triggered by Pipedrive webhook (deal stage change → auto-generate quote → update deal).

## PRD + full plan

`/Users/allenenriquez/.claude/plans/dazzling-bouncing-hippo.md`

## Why

Reduce quote time from 30–60 min to <5 min human review. Team stops measuring anything manually.
