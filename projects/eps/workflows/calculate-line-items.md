
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
| EXT-01 | External walls (low, <=3m) | $22/sqm | sqm |
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
**Do not use this skill for cleaning line items.** Cleaning jobs require writing `quote_data.json` manually — there is no calculator for cleaning. See the eps-quote skill, Stage 3b.

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

## Input Required

Either:
- **`projects/eps/.tmp/rooms.json`** already exists (from eps-measure), OR
- Text scope from Allen (e.g. "80 sqm walls, 40 sqm ceilings, 3 doors")

If rooms.json exists, load it. If not, use the text input.

Also load: `projects/eps/config/pricing.json`

---

## Calculate Areas

For each room in rooms.json, calculate applicable areas based on `surfaces` field:

| Surface | Formula |
|---|---|
| Walls (internal, standard) | `2 x (length + width) x height` |
| Ceiling (flat white) | `length x width` |
| External wall <=3m high | `2 x (length + width) x height` |
| External wall >3m high | `2 x (length + width) x height` (use EXT-02 rate) |
| Roof (tile/metal) | `length x width` of roof footprint |
| Fascia, eaves, gutters | `perimeter x 0.3m` (estimated depth) |
| Feature wall | `height x width` of single wall |

For text-only input: use the areas as given.

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
gst      = subtotal x 0.10
total    = subtotal + gst
```

---

## Output

Save to `projects/eps/.tmp/quote_data.json`:

```json
{
  "client": "...",
  "address": "...",
  "company_name": "",
  "quote_date": "YYYY-MM-DD",
  "job_description": [
    "Paint all internal walls throughout the home",
    "Paint all ceilings flat white"
  ],
  "line_items": [
    {
      "code": "INT-01",
      "description": "Internal Wall Painting",
      "quantity": 187.4,
      "rate": 22.00,
      "unit": "sqm",
      "subtotal": 4122.80
    },
    {
      "code": "EPSMOB",
      "description": "Mobilisation Fee",
      "quantity": 1,
      "rate": 100.00,
      "unit": "item",
      "subtotal": 100.00
    }
  ],
  "subtotal": 6392.00,
  "gst": 639.20,
  "total": 7031.20
}
```

---

## After Output

Print a clean summary:

```
LINE ITEMS
------------------------------------------------------
INT-01  Internal Walls         187.4 sqm x $22    $4,122.80
INT-02  Internal Ceilings       98.6 sqm x $22    $2,169.20
EPSMOB  Mobilisation Fee             1 item         $100.00
------------------------------------------------------
Subtotal                                          $6,392.00
GST (10%)                                           $639.20
TOTAL                                             $7,031.20
```

---

## Success Criteria

- `quote_data.json` written with all line items
- Math verified: subtotals sum correctly, GST = 10%, total = subtotal + GST
- Flags surfaced (day rate needed, estimated areas, etc.)
- Ready for `qa_quote.py --data-only` in the next step
