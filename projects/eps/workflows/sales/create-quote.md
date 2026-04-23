# EPS Quote Workflow

Complete SOP for creating EPS quotes. Follow this exactly — every rule, every step.

---

## Hard Rules (never break these)

1. **Job descriptions** — ALWAYS use the template from `job_descriptions/<service_type>.md`. Never invent, rewrite, summarise, or reword. Templates exist for every service type — use them. Only fill `[placeholder]` text with client context (2-3 short bullets max for JOB SUMMARY).
2. **Line items** — Split per component (walls, ceilings, skirting, doors), per apartment/unit, per level. Never lump units together. Common areas separate per level. External separate.
3. **Totals must be accurate** — Rate x quantity = correct math. No rounding tricks, no blended rates that hide components.
4. **No mobilisation fee** unless Allen explicitly says to add one. Default is NO. Never auto-include. Amount varies — only add if Allen says "add mob" or "include mobilisation."
5. **Never change approved totals** — If Allen approves a number, that number stays. Splitting line items is a formatting change, not a recalculation.
6. **Separate deals per division** — Paint → Tenders - Paint (Pipeline #4). Clean → Tenders - Clean (Pipeline #3). Never put both on the same deal.
7. **Full pipeline every time** — calculate → show Allen → create folder → copy template → fill template → link to deal. Never stop partway. Never leave placeholder text in a doc.
8. **Doc naming** — `[serviceType] Quote - [project] - [#ID if tender] - [org]`. No deal ID in the name. Project ID only for tenders (#182968 from E1). Org only if applicable.
9. **Never suggest day rates** — Allen prices on sqm rates. Don't offer day rate alternatives, comparisons, or "sanity checks." Just build the quote using sqm/unit rates from pricing.json.
10. **Show Allen line items before generating docs** — Get approval first, then generate.
11. **Tender/plan-based quotes** — Add as first JOB SUMMARY bullet: "This is a draft quote, based on plans and information available. Site visit is required to finalise."
12. **QA order** — Draft email first (no send), then run QA on doc + email together. Never run QA before drafting the email.

---

## Service Types

**Painting:** internal_painting, external_painting, roof_painting, multiple_painting, deck_stain_or_paint, commercial_painting, hourly_painting, misc_painting_repairs
**Cleaning:** construction_cleaning_1_stage, construction_cleaning_2_stage, construction_cleaning_3_stage, bond_clean, commercial_regular_cleaning, commercial_oneoff_cleaning, residential_regular_cleaning, residential_oneoff_cleaning, window_glass_cleaning, carpet_steam_cleaning, pressure_cleaning

**Two calculators — do not mix:**
- Painting → `calculate_quote.py`
- Cleaning → write `quote_data.json` manually (no calculator). See Stage 3b.

---

## Key Paths

| What | Path |
|---|---|
| Pricing config | `projects/eps/config/pricing.json` |
| Job description templates | `projects/eps/job_descriptions/<service_type>.md` |
| Quote data output | `projects/eps/.tmp/quote_data.json` |
| Rooms (from floor plan) | `projects/eps/.tmp/rooms.json` |
| Components (multi-unit) | `projects/eps/.tmp/components.json` |
| PDF output | `projects/eps/.tmp/quote_output.pdf` |
| Environment | `projects/eps/.env` |

---

## Pipeline

```
Intake → Measure → Line Items → [Allen approves] → Create Doc → Draft Email → QA → [Allen approves] → Send
```

---

## Stage 0 — Service Type & Job Description

Collect before anything else:
- **Service type(s)** — use parser-safe values from the list above
- **Client situation** — brief description

Once collected:
1. Read `projects/eps/job_descriptions/<service_type>.md`
2. Copy the template text verbatim — section by section
3. Only fill `[square bracket]` placeholders with client context — 2-3 short bullet points max
4. Preserve section headings, numbering, and spacing exactly
5. VARIATIONS is a required section — include verbatim
6. For multi-stage cleans: stage sub-sections nest inside SCOPE OF WORK string — not separate array items

**Required sections in order (one per array item in job_description JSON):**
1. JOB SUMMARY
2. SCOPE OF WORK – QUOTE INCLUSIONS
3. CLEANING METHOD
4. INCLUSIONS
5. EXCLUSIONS
6. GUARANTEES
7. VARIATIONS
8. BOOKING & PAYMENT TERMS

**Exclusion placement rule (important):**
- **Deal-specific exclusions** (e.g. "bathroom ceilings not included", "bedroom ceilings not included", client-supplied paint) go under SCOPE OF WORK as a `C. NOTES` subsection, NOT in GENERAL EXCLUSIONS.
- **GENERAL EXCLUSIONS** stays boilerplate only — asbestos, plaster repair, structural work. Same text every quote.
- Structure SCOPE OF WORK with `A/B/C` subsections: A. REPAINT WORKS (or relevant work type), B. INTERNAL AREAS (or area breakdown), C. NOTES (deal-specific exclusions, special conditions, client-supplied items).

Write the array into `projects/eps/.tmp/quote_data.json`. Also read the `<!-- quote_title: ... -->` comment from the job description template file and include it as `"quote_title"` field — required.

---

## Stage 1 — Intake

Collect:
- **Client name** — if deal ID given, fetch from Pipedrive (person name or org name). Never write "Client Name" or placeholder text.
- **Property address** — stored in a custom address field on the Pipedrive deal (not a standard field). Always check custom fields. If blank, flag it.
- **Job type**
- **Floor plan** OR **text scope**
- **Pipedrive deal ID** (optional)

Then ask about rates: **default / multiplier / custom**. Wait for Allen's answer before calculating.
Why: Quote pricing varies by job complexity and client. Never assume default.

---

## Stage 2 — Measure (Floor Plan)

**Skip if text scope provided.** Go to Stage 3.

If floor plan provided, read the floor plan using vision and extract room measurements.

### Unit conventions
- Labels in mm → divide by 1000 (4200 = 4.2m)
- Labels in m → use directly
- Scale bar (1:100) → measure relative distances and convert
- No labels, no scale → estimate using references (door = 0.9m wide, bedroom = 3.5-4.0m)

### Defaults
- Ceiling height: 2.4m unless labeled otherwise
- Open-plan living/dining: treat as one room unless clearly separated
- Include stairs, hallways, laundries if they will be painted

### What to extract per room
- Room name, length (m), width (m), height (m)
- Surfaces in scope (walls, ceiling, external)
- Whether dimensions are estimated

### Area formulas
| Surface | Formula |
|---|---|
| Walls (internal) | `2 x (length + width) x height` |
| Ceiling | `length x width` |
| External wall <=3m | `2 x (length + width) x height` |
| External wall >3m | same formula, use EXT-02 rate |
| Roof | `length x width` of roof footprint |
| Fascia/eaves/gutters | `perimeter x 0.3m` |

**Write to `projects/eps/.tmp/rooms.json`** then print summary table. Flag estimated rooms with `*`. Flag stairwells, vaulted ceilings.

**If dimensions are ambiguous, flag it — never guess silently.**

---

## Stage 3 — Line Items (Painting)

### Pricing codes

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

### Calculator usage

**Single property — use `--scope`:**
```bash
python3 tools/eps/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --scope "220sqm walls, 110sqm ceilings, 4 doors, 60lm skirting" \
  [--multiplier 1.15] \
  [--rates "INT-01:25,INT-02:24"] \
  [--date YYYY-MM-DD]
```

**Multi-unit (townhouses, levels, buildings) — use `--components`:**
```bash
python3 tools/eps/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --components projects/eps/.tmp/components.json
```

`components.json`:
```json
[
  {"label": "Townhouse 1", "scope": "220sqm walls, 110sqm ceilings, 4 doors"},
  {"label": "Townhouse 2", "scope": "200sqm walls, 100sqm ceilings, 3 doors"}
]
```

**When to use which:**
- Any job with named units (townhouse, floor, level, building, apartment) → `--components`
- Single-location jobs → `--scope`
Why: Allen wants line items split per component ("Townhouse 1 — External Wall Painting"), not aggregated.

### Measurement approach
Use aggregate whole-property measurements per floor (total wall centreline sqm, total ceiling sqm). Not room-by-room.
Why: That's how EPS actually measures — wall centreline for the whole building.

### After running calculator
1. Add `"quote_title"` to `quote_data.json` — from the `<!-- quote_title: ... -->` comment in the job description template
2. Run `python3 tools/eps/qa_quote.py --data-only` to validate structure + math
3. If QA fails, fix before proceeding
4. Print line items summary table and **STOP — wait for Allen's approval**

---

## Stage 3b — Custom Line Items (Cleaning / Lump Sum)

For cleaning jobs, write `quote_data.json` manually. No calculator.

### Builders clean line items

**2-stage builders clean:**
- Code: `EPSCLEAN-BUILD-02`
- Rate: $8.25/sqm
- ONE line item per unit: `"[Unit Label] — 2 Stage Builders Clean"`

**3-stage builders clean:**
- Code: `EPSCLEAN-BUILD-03`
- Rate: $9.00/sqm
- ONE line item per unit: `"[Unit Label] — 3 Stage Builders Clean"`

**Wrong:** three rows (Stage 1, Stage 2, Stage 3) per unit
**Right:** one row — "Townhouse 1 — 3 Stage Builders Clean" at $9.00/sqm

Window cleaning remains a separate line item per unit.

### JSON structure (all fields required by fill_quote_template.py)
```json
{
  "client": "Full Name",
  "company_name": "",
  "address": "Full address",
  "email": "client@example.com",
  "job_type": "Construction Cleaning",
  "quote_date": "YYYY-MM-DD",
  "deal_id": "",
  "quote_title": "3 Stage Construction Cleaning — [Project Name]",
  "job_description": ["section 1", "section 2", "..."],
  "line_items": [
    {"code": "EPSCLEAN-BUILD-03", "description": "Townhouse 1 — 3 Stage Builders Clean", "quantity": 95.0, "rate": 9.00, "unit": "sqm", "subtotal": 855.00}
  ],
  "subtotal": 855.00,
  "gst": 85.50,
  "total": 940.50
}
```

GST = subtotal x 0.10. Verify math before proceeding.

Run `python3 tools/eps/qa_quote.py --data-only` → fix if fails → print summary → **STOP for Allen's approval**.

---

## Stage 4 — Create Google Doc

Only proceed after Allen approves line items.

### 4a — Check for existing folder
```bash
python3 tools/eps/get_deal_folder.py --deal-id "DEAL_ID"
```

### 4b — Create folder + copy template
```bash
python3 tools/eps/create_quote_folder.py \
  --deal-id "DEAL_ID" \
  --service-type "Human Readable Service Type" \
  --client "CLIENT_FULL_NAME" \
  --division paint|clean \
  [--folder-id "EXISTING_FOLDER_ID"]
```
Capture: DOC_ID, DOC_URL, FOLDER_URL, FOLDER_NEW

### 4c — Fill and export
```bash
python3 tools/eps/fill_quote_template.py --doc-id "DOC_ID" --data "projects/eps/.tmp/quote_data.json"
python3 tools/eps/export_quote_pdf.py --doc-id "DOC_ID"
```

### 4d — Write links + value to Pipedrive
```bash
python3 tools/eps/update_pipedrive_deal.py --deal-id "DEAL_ID" --field folder --url "FOLDER_URL"  # only if new folder
python3 tools/eps/update_pipedrive_deal.py --deal-id "DEAL_ID" --field doc --url "DOC_URL"          # always
python3 tools/eps/update_pipedrive_deal.py --deal-id "DEAL_ID" --field value --value "SUBTOTAL"     # ex-GST value
```

---

## Stage 5 — Draft Email

### Template selection
| Service type | Template key |
|---|---|
| Residential painting | `quotes/residential_painting` |
| Residential cleaning | `quotes/residential_cleaning` |
| Commercial cleaning | `quotes/commercial_cleaning` |
| Builders — cleaning | `quotes/builders_cleaning` |
| Builders — painting | `quotes/builders_painting` |
| Builders — painting + cleaning | `quotes/builders_painting_cleaning` |
| Bond clean | `quotes/bond_clean` |

### Collect before drafting
- Client email, first name
- Template key
- Opener (1-line personal detail from the call)
- Situation (1 sentence: who they are + what they need)
- Concern 1 / Concern 2 (**required for residential templates**)
- Bonus line (optional complimentary item)
- Doc URL (from Stage 4)

### Tone rules
- **Residential leads** — warmer, personal, concern-led. Reference specific worries from the call.
- **Builders** — professional, proof-led. Reference company names, past projects, references.
- All emails: **under 180 words**. Simple English (3rd-5th grade). No fluff.

### Email format rules
- Use **bullet points** for key selling points — scannable, not paragraphs.
- Each concern gets its own bold-labelled bullet (e.g. **Floor protection** — ...).
- If Allen mentions a discount, include it naturally (e.g. "I was able to get you a discounted rate on this one").
- If a quote expiry date is given, bold it near the end of the email.
- Keep CTA simple: "Let me know if you'd like to lock it in."

### Draft command (no send)
```bash
python3 tools/eps/draft_quote_email.py \
  --template "quotes/<key>" \
  --first-name "Name" \
  --to "email@example.com" \
  --situation "..." \
  --opener "..." \
  --bonus "..." \
  --deal-id "123" \
  [--concern-1 "..."] \
  [--concern-2 "..."]
```

`--concern-1` and `--concern-2` are **required for residential templates** (residential_painting, residential_cleaning, bond_clean). Missing = QA will fail.

---

## Stage 6 — QA

**Draft email first (Stage 5), then QA.** QA checks doc + email together in one pass.

```bash
python3 tools/eps/qa_quote.py \
  --template "quotes/<key>" \
  --first-name "Name" \
  --to "email@example.com" \
  --situation "..." \
  --opener "..." \
  --bonus "..." \
  --deal-id "123" \
  --doc-url "GOOGLE_DOC_URL"
```

QA posts report + email draft to Pipedrive as pinned note.

- **If FAILED:** fix issues, re-draft email (Stage 5), re-run QA. Do NOT show Allen the draft.
- **If PASSED:** show Allen the email draft and wait for approval.

Full QA check details in `projects/eps/workflows/sales/qa.md`.

---

## Stage 7 — Send

After Allen approves:
```bash
python3 tools/eps/draft_quote_email.py [same args from Stage 5] --send
```

PDF at `.tmp/quote_output.pdf` attached automatically.

**STOP after sending.** Report: Google Doc URL, total (inc GST), email sent confirmation.

---

## Doc Naming Examples

- `Multiple Painting Quote - Darling Street West Social Housing (21 Units) - #182968 - Bryant Building Contractors`
- `3 Stage Construction Cleaning Quote - Darling Street West Social Housing (21 Units) - #182968 - Bryant Building Contractors`
- `Internal Painting Quote - 123 Main St, Brisbane - John Smith` (no project ID, no org — normal client)
