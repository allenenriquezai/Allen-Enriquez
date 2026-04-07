# Calculate Line Items

Generate priced line items from a scope of work. Can be run standalone or as part of `/eps-quote`.

---

## Input Required

Either:
- **`projects/eps/.tmp/rooms.json`** already exists (from `/eps-measure`), OR
- You are given a scope directly as text (e.g. "80 sqm walls, 40 sqm ceilings, 3 doors")

If rooms.json exists, load it. If not, use the text input.

Also load: `projects/eps/config/pricing.json`

---

## Calculate Areas

For each room in rooms.json, calculate applicable areas based on `surfaces` field:

| Surface | Formula |
|---------|---------|
| Walls (internal, standard) | `2 × (length + width) × height` |
| Ceiling (flat white) | `length × width` |
| External wall ≤ 3m high | `2 × (length + width) × height` |
| External wall > 3m high | `2 × (length + width) × height` (use EXT-02 rate) |
| Roof (tile/metal) | `length × width` of roof footprint |
| Fascia, eaves, gutters | `perimeter × 0.3m` (estimated depth) |
| Feature wall | `height × width` of single wall |

For text-only input: use the areas as given.

---

## Build Line Items

Match each surface to a pricing code from `pricing.json`:

| What | Code | Rate |
|------|------|------|
| Internal walls | INT-01 | $22/sqm |
| Internal ceiling | INT-02 | $22/sqm |
| Feature wall | INT-07 | $28/sqm |
| Patch & prep (minor) | INT-06 | $12/sqm — use if job is a repaint with visible wear |
| External wall (low) | EXT-01 | $22/sqm |
| External wall (high) | EXT-02 | $30/sqm |
| Fascia, eaves, gutters | EXT-03 | $20/sqm |
| Timber deck | EXT-04 | $50/sqm |
| Roof | EXT-06 | $25/sqm |

Fixed-price items (count from floor plan or ask):
- Door (both sides): INT-03 → $150 each
- Garage door: EXT-05 → $500 flat
- Skirting boards: INT-04 → $10/lm (use total room perimeter)
- Architraves: INT-05 → $9/lm (use total room perimeter)

**Always include:**
- Mobilisation fee: EPSMOB → $100 (every job)

**Day rate fallback:**
If the job has flags (stairwell, vaulted ceiling, heritage building, severe damage), quote by:
- Day rate: $1,300/painter/day
- Hourly: $160/painter/hr
Note this in the output and explain why.

---

## Totals

```
subtotal  = sum of all line item subtotals
gst       = subtotal × 0.10
total     = subtotal + gst
```

---

## Job Description

Write 3–5 bullet points describing what will be done. Plain English, max 5th grade reading level. Client-facing — no jargon, no measurements.

Example:
- Paint all internal walls throughout the home with two coats of premium paint
- Paint all ceilings flat white
- All doors painted both sides including frames
- Minor patching and prep work included throughout

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
      "code": "INT-02",
      "description": "Internal Ceiling Painting",
      "quantity": 98.6,
      "rate": 22.00,
      "unit": "sqm",
      "subtotal": 2169.20
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
──────────────────────────────────────────────────────
INT-01  Internal Walls         187.4 sqm × $22    $4,122.80
INT-02  Internal Ceilings       98.6 sqm × $22    $2,169.20
EPSMOB  Mobilisation Fee             1 item         $100.00
──────────────────────────────────────────────────────
Subtotal                                          $6,392.00
GST (10%)                                           $639.20
TOTAL                                             $7,031.20
```
