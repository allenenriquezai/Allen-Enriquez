# EPS Quote Workflow

Full pipeline: intake → measure → line items → Google Doc → Pipedrive.
Chains `/eps-measure` and `/eps-lineitems` in sequence.

---

## Stage 0 — Service Type & Client Context

Collect before anything else:

- **Service type(s)** — use parser-safe values:
  - Paint: `internal_painting`, `external_painting`, `roof_painting`, `multiple_painting`, `deck_stain_or_paint`, `commercial_painting`, `hourly_painting`, `day_rate_painting`, `misc_painting_repairs`
  - Clean: `construction_cleaning_1_stage`, `construction_cleaning_2_stage`, `construction_cleaning_3_stage`, `bond_clean`, `commercial_regular_cleaning`, `commercial_oneoff_cleaning`, `residential_regular_cleaning`, `residential_oneoff_cleaning`, `window_glass_cleaning`, `carpet_steam_cleaning`, `pressure_cleaning`
  - Multiple types allowed — list all that apply
- **Client situation** — brief description (e.g. "selling in 6 weeks, wants a fresh look")
- **Emotional drivers** — what's motivating this (e.g. "stressed about bond, real estate gave them a list")

Once collected:
1. Read `projects/eps/job_descriptions/<service_type>.md` for each service type
2. Identify the relevant variant (e.g. new construction vs repaint, 1/2/3-stage clean)
3. Copy the template text verbatim — do **not** rewrite, summarise, or paraphrase any section

**Job description rules (strictly enforced):**
- The template is the output. Copy it exactly, section by section.
- Only fill in the placeholder text marked with `[square brackets]` using client context (e.g. `[Builder or project situation – rewritten professionally if provided.]`) — 2–3 short bullet points max, plain English
- Each top-level section in the template = one string in the `job_description` JSON array
- Preserve the section heading, numbering, and spacing exactly as it appears in the template
- For multi-stage cleans: Stage sub-sections (Stage 1, Stage 2, Stage 3) are nested inside the SCOPE OF WORK string — **not** separate array items
- VARIATIONS is a required section — include it verbatim from the template
- Do NOT collapse, merge, or reword sections

**Required sections in order (one per array item), copied verbatim from template:**
```
"JOB SUMMARY\n* [fill placeholder with client context]\n* [remaining bullets verbatim]"
"1. SCOPE OF WORK – QUOTE INCLUSIONS\n* ...\n\nSTAGE 1 – ...\n\nSTAGE 2 – ...\n\nSTAGE 3 – ..."
"2. CLEANING METHOD\n* ..."
"3. INCLUSIONS\n* ..."
"4. QUOTE EXCLUSIONS\n* ..."
"5. GUARANTEES\n* ..."
"6. VARIATIONS\n* ..."
"7. BOOKING & PAYMENT TERMS\n* ..."
```

For multiple service types, merge the SCOPE OF WORK sections only; all other sections stay verbatim.

**STOP — do not run `fill_quote_template.py` until `job_description` is written into `quote_data.json`.**

Write the array into the `job_description` field of `projects/eps/.tmp/quote_data.json`.

---

## Stage 1 — Intake

Collect the following. If anything is missing, stop and ask.

Required:
- **Client name**
- **Property address**
- **Job type** — e.g. internal repaint, external, ceilings only, full repaint, new build
- **Floor plan** OR **text scope** — one of:
  - Local file path (image or PDF)
  - Google Drive link
  - Text description: "Living room ~40sqm walls + ceiling, 2 doors"
- **Pipedrive deal ID** (optional — if provided, doc link will be written to the deal)

Once you have the required info, ask about rates before proceeding.

---

## Stage 1b — Rate Selection

Ask:

> "What rates do you want to use?
> - **Default** — use standard pricing from pricing.json
> - **Multiplier** — apply a % increase across all rates (e.g. +15% → `--multiplier 1.15`)
> - **Custom** — set specific rates per item (e.g. `INT-01:25, INT-02:24`)"

Wait for the answer. Then proceed.

---

## Stage 2 — Measure

If a floor plan file was provided:
- Follow `projects/eps/workflows/measure-floor-plan.md` exactly
- Output: `projects/eps/.tmp/rooms.json`

If text scope was provided (no floor plan):
- Skip to Stage 3 — pass the text directly as input

---

## Stage 3 — Line Items

**Single scope (whole property):**
```
python3 tools/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --scope "SCOPE_STRING" \
  [--mob AMOUNT] \
  [--date YYYY-MM-DD]
```

**Multi-component (per unit / per level / per townhouse):**
```
python3 tools/calculate_quote.py \
  --client "CLIENT_NAME" \
  --address "PROPERTY_ADDRESS" \
  --job-type "JOB_TYPE" \
  --components projects/eps/.tmp/components.json \
  [--mob AMOUNT]
```

`components.json` format:
```json
[
  {"label": "Townhouse 1", "scope": "220sqm walls, 110sqm ceilings, 4 doors"},
  {"label": "Townhouse 2", "scope": "200sqm walls, 100sqm ceilings, 3 doors"}
]
```
Use `--components` whenever the job has multiple separate units, levels, or buildings. Each component becomes its own set of line items (e.g. "Townhouse 1 — Internal Wall Painting").

- `--mob` is optional — only include if a mobilisation fee applies; amount varies per job
- `--date` defaults to today if omitted

Output: `projects/eps/.tmp/quote_data.json`

**After running:** open `quote_data.json` and add the `quote_title` field manually:
```json
"quote_title": "Internal Painting — Full Home Repaint"
```
Read the `<!-- quote_title: ... -->` comment at the top of `job_descriptions/<service_type>.md` for the correct value. This field is **required** — `create_sm8_deposit.py` will crash without it.

### Stage 3b — Custom Line Items (skip calculator)

When the client gives a lump-sum price (not per-sqm rates), skip `calculate_quote.py` and write `quote_data.json` directly.

Write to `projects/eps/.tmp/quote_data.json` using this schema:

```json
{
  "client": "Full Name",
  "company_name": "",
  "address": "Full address",
  "email": "client@example.com",
  "job_type": "roof painting",
  "quote_date": "YYYY-MM-DD",
  "deal_id": "",
  "quote_title": "Roof Painting — Main Residence",
  "job_description": ["bullet 1", "bullet 2"],
  "line_items": [
    {
      "code": "EXT-06",
      "description": "Main Roof — Roof Painting",
      "quantity": 1,
      "rate": 11567.35,
      "unit": "item",
      "subtotal": 11567.35
    }
  ],
  "subtotal": 11567.35,
  "gst": 1156.74,
  "total": 12724.09
}
```

**All fields required by `fill_quote_template.py`:**
- `client` → `[personName]`
- `company_name` → `[organizationName]` (blank if none)
- `address` → `[projectAddress]`
- `email` → `[personEmail]` (blank if unknown)
- `quote_date` → `[Short today's date (datetime today_short)]`
- `deal_id` → `[Deal ID (deal id)]` (blank if none)
- `job_description` → `[jobDescription]` (array of strings, joined with newlines)
- `line_items` → table rows: each needs `code`, `description`, `quantity`, `rate`, `unit`, `subtotal`
- `subtotal`, `gst`, `total` → totals table (GST = subtotal × 0.10)

Then skip to Stage 4.

---

Supported scope tokens (for Stage 3 only):
- `Xsqm walls` / `Xsqm ceilings` / `X doors` / `Xsqm feature wall` / `Xsqm patch` / `Xlm skirting` / `Xlm architraves`
- `Xsqm external walls` / `Xsqm external walls >3m` / `Xsqm roof` / `X garage doors` / `Xlm fascia` / `Xsqm deck`

When Togal.AI is available: use its aggregate area output directly as the `--scope` string.

---

## Stage 3.5 — Pre-Doc Data QA (blocking)

Before creating the Google Doc, validate quote_data.json. This catches job description and line item issues before any API calls are made.

```
python3 tools/qa_quote.py --data-only
```

Checks:
- All required fields present (client, address, job_type, quote_date, email)
- Job description has all 7 sections: JOB SUMMARY, SCOPE OF WORK, CLEANING METHOD, INCLUSIONS, EXCLUSIONS, GUARANTEES, BOOKING & PAYMENT TERMS
- Line item math correct (subtotals sum = subtotal; GST = 10%; total = subtotal + GST)

**If FAILED: fix quote_data.json before proceeding. Do NOT create the Google Doc until this passes.**

---

## Stage 4 — Create Google Doc

### Step 4a — Check for existing folder (if deal ID was provided)

```
python3 tools/get_deal_folder.py --deal-id "DEAL_ID"
```

Capture the output (one line). If non-empty, that is the existing folder ID — use it in Step 4b.

### Step 4b — Create folder and copy template

If an existing folder ID was found in Step 4a:
```
python3 tools/create_quote_folder.py \
  --deal-id "DEAL_ID" \
  --service-type "Human Readable Service Type" \
  --client "CLIENT_FULL_NAME" \
  --division paint|clean \
  --folder-id "EXISTING_FOLDER_ID"
```

If no existing folder (Step 4a returned blank, or no deal ID was given):
```
python3 tools/create_quote_folder.py \
  --deal-id "DEAL_ID" \
  --service-type "Human Readable Service Type" \
  --client "CLIENT_FULL_NAME" \
  --division paint|clean
```

Capture from the output:
- Line 1 → `DOC_ID`
- Line 2 → `DOC_URL`
- Line starting with `FOLDER:` → `FOLDER_URL`
- Line `FOLDER_NEW: true` → new folder was created (write it back to Pipedrive in Step 4d)

### Step 4c — Fill and export

```
python3 tools/fill_quote_template.py --doc-id "DOC_ID" --data "projects/eps/.tmp/quote_data.json"
python3 tools/export_quote_pdf.py --doc-id "DOC_ID"
```

Output: `projects/eps/.tmp/quote_output.pdf`

---

## Stage 4b — Update Pipedrive (if deal ID was provided)

### Step 4d — Write links to Pipedrive

If a new folder was created (`FOLDER_NEW: true` in Step 4b output):
```
python3 tools/update_pipedrive_deal.py --deal-id "DEAL_ID" --field folder --url "FOLDER_URL"
```

Always write the doc link:
```
python3 tools/update_pipedrive_deal.py --deal-id "DEAL_ID" --field doc --url "DOC_URL"
```

---

## Output

Return to Allen:
- Google Doc link
- Total: $X,XXX (inc GST)
- Any flags from the measurement stage (stairwells, estimated dimensions, etc.)

---

---

## Stage 5 — QA Check + Draft Email to Pipedrive

Collect before running:
- **Client email address**
- **Template key** (see table below)
- **Opener** — optional 1-line personal detail from the call (default: "It was great talking to you.")
- **Situation** — 1 sentence: who they are + what they need + timing
- **Concern 1 / Concern 2** — real buying concerns raised on the call (residential templates only)
- **Bonus line** — any complimentary item to highlight (optional)
- **Doc URL** — Google Doc link from Stage 4

| Service type | Template key |
|---|---|
| Residential painting | `quotes/residential_painting` |
| Residential cleaning | `quotes/residential_cleaning` |
| Commercial cleaning (regular or one-off) | `quotes/commercial_cleaning` |
| Builders — cleaning only | `quotes/builders_cleaning` |
| Builders — painting only | `quotes/builders_painting` |
| Builders — painting + cleaning | `quotes/builders_painting_cleaning` |
| Bond clean | `quotes/bond_clean` |

**Step 1 — Draft email first (no send):**
```
python3 tools/draft_quote_email.py \
  --template "quotes/builders_cleaning" \
  --first-name "Jane" \
  --to "jane@example.com" \
  --situation "7-townhouse project nearing completion, needs 3-stage clean before handover" \
  --opener "Good talking to you earlier." \
  --bonus "Window and glass cleaning included across all townhouses." \
  --deal-id "123"
```

For **residential templates only**, also include:
```
  --concern-1 "Will it be done before the open home?" \
  --concern-2 "How disruptive will the painters be?"
```
These map to `[concern1]` / `[concern2]` placeholders in residential templates. If omitted on a residential email, QA will fail with unfilled placeholders.

**Step 2 — Run QA on both quote doc and email draft together:**
```
python3 tools/qa_quote.py \
  --template "quotes/builders_cleaning" \
  --first-name "Jane" \
  --to "jane@example.com" \
  --situation "7-townhouse project nearing completion, needs 3-stage clean before handover" \
  --opener "Good talking to you earlier." \
  --bonus "Window and glass cleaning included across all townhouses." \
  --deal-id "123" \
  --doc-url "GOOGLE_DOC_URL"
```

QA checks:
- All required fields present in quote_data.json
- Job description has all 7 sections (JOB SUMMARY, SCOPE OF WORK, CLEANING METHOD, INCLUSIONS, EXCLUSIONS, GUARANTEES, BOOKING & PAYMENT TERMS)
- Line item math correct (subtotal + GST = total)
- No unfilled [placeholders] in email body
- Email under 180 words

**If FAILED: fix issues, re-draft email (Step 1), then re-run QA (Step 2). Do NOT show Allen anything until QA passes.**
On pass: QA report + email draft posted as pinned note on Pipedrive deal. Show Allen the email draft from QA output and wait for approval.

**Step 3 — Export PDF (before sending):**
```
python3 tools/export_quote_pdf.py --doc-id "DOC_ID"
```
Output: `projects/eps/.tmp/quote_output.pdf` — this will be auto-attached to the email.

**Step 4 — Send (after Allen approves):**
```
python3 tools/draft_quote_email.py \
  --template "quotes/builders_cleaning" \
  --first-name "Jane" \
  --to "jane@example.com" \
  --situation "..." \
  --opener "..." \
  --bonus "..." \
  --deal-id "123" \
  --send
```
The PDF at `.tmp/quote_output.pdf` is attached automatically. If it's missing, a warning is printed and the email sends without it.

Templates live in: `projects/eps/templates/email/quotes/`

---

## Notes

- Pricing config: `projects/eps/config/pricing.json`
- Temp files: `projects/eps/.tmp/` (disposable — safe to overwrite between quotes)
- Quote template ID: set in `pricing.json` under `"template_doc_id"`
- If floor plan dimensions are unclear, flag it — do not guess silently
