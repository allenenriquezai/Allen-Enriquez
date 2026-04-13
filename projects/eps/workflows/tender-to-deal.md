
# Tender-to-Deal Pipeline

Convert an EstimateOne tender into a Pipedrive deal with a quote attached.

---

## Prerequisites
- E1 scrape completed (`e1_latest.json` exists)
- Pipedrive API key configured in `projects/eps/.env`
- Google auth token valid (`projects/eps/token_eps.pickle`)

---

## Stage 1 — Select Tender

Input: project_id from E1 scrape data or Google Sheet.

```bash
# Load tender data
python3 -c "
import json
data = json.load(open('projects/eps/.tmp/estimateone/e1_latest.json'))
# Find tender by project_id
for section in ['leads', 'open_tenders']:
    for t in data.get('sections', {}).get(section, []):
        if t.get('project_id', '').replace('#','') == 'PROJECT_ID':
            print(json.dumps(t, indent=2))
"
```

Extract: project name, builder, budget, category, due date, address.

---

## Stage 2 — Download Documents

```bash
python3 tools/estimateone_scraper.py --download-docs --project-ids PROJECT_ID --no-headless
```

Output: PDFs saved to `projects/eps/.tmp/estimateone/docs/{project_id}/`

If `--leads` or `--open` not specified, the scraper loads from `e1_latest.json` automatically.

---

## Stage 3 — Analyze Documents

```bash
python3 tools/analyze_tender_docs.py --project-id PROJECT_ID --project-name "PROJECT_NAME"
```

Output: `projects/eps/.tmp/estimateone/briefs/{project_id}_brief.json`

Contains: trades_required, scope_summary, areas_mentioned, key_dates, special_conditions, paint_spec, cleaning_stages, estimated_value.

---

## Gate 1 — Allen Reviews Brief

Present to Allen:
- **Project:** name, address, budget range
- **Builder:** who's running the tender
- **Scope:** summary from brief
- **Trades:** painting, cleaning, or both
- **Due:** tender closing date
- **Estimated value:** from brief analysis
- **Special conditions:** any flags

Ask: **Pursue this tender? Which trades?**

If skip → log reason, end pipeline.
If pursue → proceed with selected trades.

---

## Stage 4 — Create CRM Records

### 4a — Organization (builder)
```bash
# Search first (dedup)
python3 tools/pipedrive_create.py --action create-org --name "BUILDER_NAME" --address "BUILDER_LOCATION"
```
Capture: `ORG_ID`

### 4b — Person (contact at builder, if known)
```bash
python3 tools/pipedrive_create.py --action create-person --name "CONTACT_NAME" --org-id ORG_ID --email "EMAIL" --phone "PHONE"
```
Capture: `PERSON_ID`

If no contact info available from E1, skip — deal can be created without a person.

### 4c — Create Deal(s)
One deal per trade. Title format: `{Project Name} - Painting` or `{Project Name} - Cleaning`.

```bash
# Painting deal → Pipeline 4 (Tenders - Paint)
python3 tools/pipedrive_create.py --action create-deal \
  --title "PROJECT_NAME - Painting" \
  --org-id ORG_ID --person-id PERSON_ID \
  --pipeline-id 4 --stage-id QUOTE_IN_PROGRESS_STAGE_ID \
  --value ESTIMATED_VALUE

# Cleaning deal → Pipeline 3 (Tenders - Clean)
python3 tools/pipedrive_create.py --action create-deal \
  --title "PROJECT_NAME - Cleaning" \
  --org-id ORG_ID --person-id PERSON_ID \
  --pipeline-id 3 --stage-id QUOTE_IN_PROGRESS_STAGE_ID \
  --value ESTIMATED_VALUE
```
Capture: `DEAL_ID` for each.

### 4d — Post tender note to deal
Post a pinned note with tender details (project ID, E1 link, brief summary, due date).

---

## Stage 5 — Attach Documents

### 5a — Create Google Drive folder
```bash
python3 tools/create_quote_folder.py \
  --deal-id DEAL_ID \
  --service-type "SERVICE_TYPE" \
  --client "BUILDER_NAME" \
  --division paint|clean
```
Capture: `FOLDER_URL`, `DOC_ID`

### 5b — Upload tender docs to folder
Upload downloaded PDFs from `docs/{project_id}/` to the Google Drive folder.

### 5c — Link folder to deal
```bash
python3 tools/update_pipedrive_deal.py --deal-id DEAL_ID --field folder --url "FOLDER_URL"
```

---

## Stage 6 — Measure (if plans available)

If `brief.has_plans == true`:

Follow `projects/eps/workflows/measure-floor-plan.md`:
1. Read plan PDFs from `docs/{project_id}/` using vision
2. Output: `projects/eps/.tmp/rooms.json`

If no plans: use areas_mentioned from brief, or ask Allen for scope description.

---

## Stage 7 — Generate Quote

Follow `projects/eps/workflows/create-quote.md`:
1. Service type from brief (e.g., "internal_painting", "construction_cleaning_3_stage")
2. Client = builder name
3. Address = project address
4. Scope = from rooms.json or brief analysis
5. Ask Allen for rate preference (default / multiplier / custom)

Output: quote_data.json → Google Doc → PDF

---

## Gate 2 — Allen Reviews Quote

Present:
- Quote total (inc GST)
- Line items summary
- Google Doc link
- Any flags (estimated dimensions, special conditions)

Ask: **Send this quote? Adjust rates? Revise scope?**

If revise → go back to relevant stage.
If approve → proceed.

---

## Stage 8 — Submit

### 8a — Move deal stage
```bash
# Move to QUOTE SENT
curl -s -X PUT "https://${DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"stage_id": QUOTE_SENT_STAGE_ID}'
```

### 8b — Create follow-up activity (2 weeks out)
```bash
curl -s -X POST "https://${DOMAIN}/api/v1/activities?api_token=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Follow up on tender quote - PROJECT_NAME",
    "type": "call",
    "deal_id": DEAL_ID,
    "due_date": "YYYY-MM-DD",
    "due_time": "09:00",
    "note": "Follow up on tender quote submitted via E1. Check if they received it and if there are any questions."
  }'
```

### 8c — Submit quote through E1 (if applicable)
For leads (invitations): submit through EstimateOne platform.
For open tenders: email directly or submit through E1.

### 8d — Post completion note
Pin a note to the deal: "Quote submitted [date]. Follow-up scheduled [date]. Total: $X,XXX inc GST."

---

## Builder Lead Flow (Cold Outreach)

Separate from the quoting pipeline. For builders identified from E1 directory or tender listings:

```bash
# Create org
python3 tools/pipedrive_create.py --action create-org --name "BUILDER_NAME" --address "LOCATION"

# Create person (if contact known)
python3 tools/pipedrive_create.py --action create-person --name "CONTACT" --org-id ORG_ID --phone "PHONE"

# Create lead for cold calling
python3 tools/pipedrive_create.py --action create-lead --title "BUILDER_NAME - E1 Builder" --org-id ORG_ID --person-id PERSON_ID
```

Leads appear in Pipedrive's Leads inbox for cold call outreach.

---

## Temp Files

| File | Contents |
|---|---|
| `projects/eps/.tmp/estimateone/docs/{id}/` | Downloaded tender PDFs |
| `projects/eps/.tmp/estimateone/briefs/{id}_brief.json` | Analyzed tender brief |
| `projects/eps/.tmp/rooms.json` | Room measurements (from plan analysis) |
| `projects/eps/.tmp/quote_data.json` | Generated quote data |
| `projects/eps/.tmp/quote_output.pdf` | Exported quote PDF |

---

## Rules

- Never skip Gate 1 — Allen must approve pursuit
- Never send a quote without Gate 2 approval
- Always search before creating CRM records (dedup)
- Post summary notes to deals at each stage transition
- If measurement is estimated, flag it in the quote
