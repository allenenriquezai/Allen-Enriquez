# EPS Quote Skill

Owns: intake, job description, Google Doc creation, and email template mapping.
Delegates: measurement (eps-measure), line items (eps-lineitems), QA (eps-qa).

---
## Domain Knowledge

### Service types
- **Painting:** internal_painting, external_painting, roof_painting, multiple_painting, deck_stain_or_paint, commercial_painting, hourly_painting, day_rate_painting, misc_painting_repairs
- **Cleaning:** construction_cleaning_1_stage, construction_cleaning_2_stage, construction_cleaning_3_stage, bond_clean, commercial_regular_cleaning, commercial_oneoff_cleaning, residential_regular_cleaning, residential_oneoff_cleaning, window_glass_cleaning, carpet_steam_cleaning, pressure_cleaning

### Two calculators — do not mix them
- **Painting** -> `calculate_quote.py` via eps-lineitems skill
- **Cleaning** -> write `quote_data.json` manually (no calculator — lump sum or sqm x rate). See Stage 3b.

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
## Pipeline

```
Intake -> Measure -> Line Items -> Create Doc -> Draft Email -> QA -> Show Allen
```

One QA pass at the end on the complete package. If QA fails, fix and re-run from wherever the issue is.

---
## Stage 0 — Service Type & Job Description

Collect before anything else:
- **Service type(s)** — use parser-safe values from the list above
- **Client situation** — brief description
- **Emotional drivers** — what's motivating this

Once collected:
1. Read `projects/eps/job_descriptions/<service_type>.md`
2. Identify the relevant variant
3. Copy the template text verbatim

**Job description rules:**
- The template is the output. Copy it exactly, section by section.
- Only fill `[square bracket]` placeholders with client context — 2-3 short bullet points max
- Preserve section heading, numbering, and spacing exactly
- VARIATIONS is a required section — include verbatim
- Do NOT collapse, merge, or reword sections

**Required sections in order (one per array item):**
1. JOB SUMMARY
2. SCOPE OF WORK – QUOTE INCLUSIONS
3. CLEANING METHOD
4. INCLUSIONS
5. QUOTE EXCLUSIONS
6. GUARANTEES
7. VARIATIONS
8. BOOKING & PAYMENT TERMS

Write the array into `projects/eps/.tmp/quote_data.json`.

---
## Stage 1 — Intake

Collect:
- **Client name**
- **Property address**
- **Job type**
- **Floor plan** OR **text scope**
- **Pipedrive deal ID** (optional)

Then ask about rates (default / multiplier / custom). Wait for the answer.

---
## Stage 2 — Measure

If floor plan provided: **eps-measure** skill -> output `rooms.json`.
If text scope: skip to Stage 3.

---
## Stage 3 — Line Items

**eps-lineitems** skill -> output `quote_data.json`.

### Stage 3b — Custom Line Items (skip calculator)
For lump-sum or cleaning jobs, write `quote_data.json` directly:

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
  "job_description": ["section 1", "section 2"],
  "line_items": [
    {"code": "EXT-06", "description": "Main Roof", "quantity": 1, "rate": 11567.35, "unit": "item", "subtotal": 11567.35}
  ],
  "subtotal": 11567.35,
  "gst": 1156.74,
  "total": 12724.09
}
```

All fields required by `fill_quote_template.py`. GST = subtotal x 0.10.

---
## Stage 4 — Create Google Doc

### 4a — Check for existing folder
```bash
python3 tools/get_deal_folder.py --deal-id "DEAL_ID"
```
### 4b — Create folder + copy template
```bash
python3 tools/create_quote_folder.py \
  --deal-id "DEAL_ID" \
  --service-type "Human Readable Service Type" \
  --client "CLIENT_FULL_NAME" \
  --division paint|clean \
  [--folder-id "EXISTING_FOLDER_ID"]
```
Capture: `DOC_ID`, `DOC_URL`, `FOLDER_URL`, `FOLDER_NEW: true/false`
### 4c — Fill and export
```bash
python3 tools/fill_quote_template.py --doc-id "DOC_ID" --data "projects/eps/.tmp/quote_data.json"
python3 tools/export_quote_pdf.py --doc-id "DOC_ID"
```
### 4d — Write links to Pipedrive
```bash
python3 tools/update_pipedrive_deal.py --deal-id "DEAL_ID" --field folder --url "FOLDER_URL"  # only if new folder
python3 tools/update_pipedrive_deal.py --deal-id "DEAL_ID" --field doc --url "DOC_URL"          # always
```

---
## Stage 5 — Draft Email

Collect:
- Client email, template key, opener, situation, bonus line, doc URL
- For residential templates: concern-1 and concern-2 (required)

| Service type | Template key |
|---|---|
| Residential painting | `quotes/residential_painting` |
| Residential cleaning | `quotes/residential_cleaning` |
| Commercial cleaning | `quotes/commercial_cleaning` |
| Builders — cleaning | `quotes/builders_cleaning` |
| Builders — painting | `quotes/builders_painting` |
| Builders — painting + cleaning | `quotes/builders_painting_cleaning` |
| Bond clean | `quotes/bond_clean` |

```bash
python3 tools/draft_quote_email.py \
  --template "quotes/<key>" \
  --first-name "Name" \
  --to "email@example.com" \
  --situation "..." \
  --opener "..." \
  --bonus "..." \
  --deal-id "123"
```

---
## Stage 6 — QA + Show Allen

Run **eps-qa** skill on the complete package (quote data + doc + email draft).
If QA passes: post to Pipedrive as pinned note. Allen reviews and approves.

After Allen approves:
```bash
python3 tools/draft_quote_email.py [same args] --send
```
PDF at `.tmp/quote_output.pdf` is attached automatically.

---
## Temp Files

| File | Contains |
|---|---|
| `projects/eps/.tmp/rooms.json` | Room measurements from floor plan |
| `projects/eps/.tmp/quote_data.json` | Full quote data |
| `projects/eps/.tmp/quote_output.pdf` | Exported PDF |

---
## Success Criteria

Return to Allen:
- Google Doc URL
- Total: $X,XXX inc GST
- Any flags (estimated dimensions, stairwells, missing address, etc.)