---
name: eps-lineitems
description: Use when calculating priced line items from a scope of work for an EPS painting job. Triggered when a scope of work needs to be broken down into line items with pricing.
disable-model-invocation: true
---

# EPS Line Items Skill

Generate priced line items from a scope of work. Output `quote_data.json`.

---

## Domain Knowledge

### Painting pricing codes (from pricing.json)

| Code | Surface | Rate | Unit |
|---|---|---|---|
| INT-01 | Internal walls (standard) | $22/sqm | sqm |
| INT-02 | Internal ceilings (flat white) | $22/sqm | sqm |
| INT-03 | Door (both sides + frame) | $150 | each |
| INT-04 | Skirting boards | $10/lm | lm |
| INT-05 | Architraves | $9/lm | lm |
| INT-06 | Patch & prep (repaint with wear) | $12/sqm | sqm |
| INT-07 | Feature wall | $28/sqm | sqm |
| EXT-01 | External walls (low, ≤3m) | $22/sqm | sqm |
| EXT-02 | External walls (high, >3m) | $30/sqm | sqm |
| EXT-03 | Fascia, eaves, gutters | $20/sqm | sqm |
| EXT-04 | Timber deck | $50/sqm | sqm |
| EXT-05 | Garage door | $500 | each |
| EXT-06 | Roof | $25/sqm | sqm |
| EPSMOB | Mobilisation fee | $100 | item |

**Mob fee is optional** — only include if Allen says it applies. Amount may vary.

### Day rate fallback
Use when: stairwell, vaulted ceiling, heritage building, or severe damage flagged.
- Day rate: $1,300/painter/day
- Hourly: $160/painter/hr
Always note why the day rate was used.

### Cleaning
**Do not use this skill for cleaning line items.** Cleaning jobs require writing `quote_data.json` manually — there is no calculator for cleaning. Refer to create-quote.md Stage 3b.

### Scope tokens (for calculate_quote.py)
`Xsqm walls`, `Xsqm ceilings`, `X doors`, `Xsqm feature wall`, `Xsqm patch`, `Xlm skirting`, `Xlm architraves`, `Xsqm external walls`, `Xsqm external walls >3m`, `Xsqm roof`, `X garage doors`, `Xlm fascia`, `Xsqm deck`

---

## Decision Logic

| Situation | Action |
|---|---|
| `rooms.json` exists in `.tmp/` | Load it — use total areas as scope input |
| No `rooms.json` | Use text scope directly from Allen |
| Stairwell or vaulted ceiling flagged | Offer day rate option before calculating sqm |
| Multiplier requested | Pass `--multiplier X.XX` to calculate_quote.py |
| Custom rates requested | Pass `--rates "INT-01:25,INT-02:24"` |
| Mob fee applies | Add `--mob AMOUNT` |
| Cleaning job | Do not run calculator — write quote_data.json manually |
| Multi-unit job (townhouses, levels, buildings) | Use `--components` not `--scope` |

---

## Tool

**Single scope (whole property):**
```bash
python3 tools/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --scope "220sqm walls, 110sqm ceilings, 4 doors, 60lm skirting" \
  [--mob AMOUNT] \
  [--multiplier 1.15] \
  [--date YYYY-MM-DD]
```

**Multi-component (per unit / per level / per townhouse):**
```bash
python3 tools/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --components projects/eps/.tmp/components.json \
  [--mob AMOUNT]
```

`components.json`:
```json
[
  {"label": "Townhouse 1", "scope": "220sqm walls, 110sqm ceilings, 4 doors"},
  {"label": "Townhouse 2", "scope": "200sqm walls, 100sqm ceilings, 3 doors"}
]
```

Use `--components` for any job with multiple units, levels, or buildings. Use `--scope` for single-property jobs only.

Output: `projects/eps/.tmp/quote_data.json`

**After running:** add `quote_title` to `quote_data.json` manually:
```json
"quote_title": "Internal Painting — Full Home Repaint"
```
Read the `<!-- quote_title: ... -->` comment from `job_descriptions/<service_type>.md`. Required — `create_sm8_deposit.py` crashes without it.

---

## Totals (verify after running)

```
subtotal = sum of all line item subtotals
gst      = subtotal × 0.10
total    = subtotal + gst
```

---

## Success Criteria

- `quote_data.json` written with all line items
- Math verified: subtotals sum correctly, GST = 10%, total = subtotal + GST
- Flags surfaced (day rate needed, estimated areas, etc.)
- Ready for `qa_quote.py --data-only` in the next step

---

## Full workflow reference
`projects/eps/workflows/calculate-line-items.md`
