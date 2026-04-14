# Tender Pipeline

Full E1 tender pipeline: scrape > filter > download docs > analyze > Gate 1 > CRM > measure > quote > Gate 2 > submit.

---

## Tools

| Tool | Purpose |
|---|---|
| `tools/estimateone_scraper.py` | Scrape E1 leads, open tenders, builders, docs |
| `tools/tender_batch.py` | Daily automation — full pipeline in one command |
| `tools/analyze_tender_docs.py` | Analyze specs > generate brief |
| `tools/e1_to_sheet.py` | Push scrape data to Google Sheet |
| `tools/pipedrive_create.py` | Create org, person, deal, lead |
| `tools/calculate_quote.py` | Generate line items + pricing |
| `tools/update_pipedrive_deal.py` | Link folder/doc to deal |

---

## Scraper commands

```bash
# Daily scrape — leads + open tenders filtered by trades
python3 tools/estimateone_scraper.py --leads --open --filter-trades "Painting,Building Cleaning"

# Full scrape with doc download
python3 tools/estimateone_scraper.py --leads --open --download-docs --auto-express-interest --filter-trades "Painting,Building Cleaning"

# Full daily batch (scrape > analyze > CRM > sheet)
python3 tools/tender_batch.py

# Dry run
python3 tools/tender_batch.py --dry-run
```

---

## Data flow

```
EstimateOne > estimateone_scraper.py > e1_latest.json > e1_to_sheet.py > Google Sheet
                                     |
                       --download-docs > docs/{project_id}/ > analyze_tender_docs.py > brief
                                                                                      |
                                                                        pipedrive_create.py > Pipedrive deal
                                                                                            |
                                                                                  calculate_quote.py > quote
```

---

## Pipeline stages

```
SCRAPE > FILTER TRADES > DOWNLOAD DOCS > ANALYZE > [GATE 1] > CRM SETUP > MEASURE > QUOTE > [GATE 2] > SUBMIT
```

### Stage 1 — Select tender

Load from `e1_latest.json` by project_id. Extract: project name, builder, budget, category, due date, address.

### Stage 2 — Download documents

```bash
python3 tools/estimateone_scraper.py --download-docs --project-ids PROJECT_ID --no-headless
```

Output: PDFs in `projects/eps/.tmp/estimateone/docs/{project_id}/`

### Stage 3 — Analyze documents

```bash
python3 tools/analyze_tender_docs.py --project-id PROJECT_ID --project-name "PROJECT_NAME"
```

Output: `projects/eps/.tmp/estimateone/briefs/{project_id}_brief.json`

### Gate 1 — Allen reviews brief

Present: project name, address, budget, builder, scope summary, trades, due date, estimated value, special conditions.

Ask: **Pursue? Which trades? Skip?**

Skip = log reason, end pipeline.
Pursue = proceed with selected trades.

### Stage 4 — Create CRM records

**Always search before creating (dedup).**

```bash
# 4a — Org (builder)
python3 tools/pipedrive_create.py --action create-org --name "BUILDER_NAME" --address "LOCATION"

# 4b — Person (if contact known)
python3 tools/pipedrive_create.py --action create-person --name "CONTACT" --org-id ORG_ID --email "EMAIL" --phone "PHONE"

# 4c — Deal(s) — one per trade
# Painting > Pipeline 4 (Tenders - Paint)
python3 tools/pipedrive_create.py --action create-deal \
  --title "PROJECT_NAME - Painting" \
  --org-id ORG_ID --person-id PERSON_ID \
  --pipeline-id 4 --stage-id 35 \
  --value ESTIMATED_VALUE

# Cleaning > Pipeline 3 (Tenders - Clean)
python3 tools/pipedrive_create.py --action create-deal \
  --title "PROJECT_NAME - Cleaning" \
  --org-id ORG_ID --person-id PERSON_ID \
  --pipeline-id 3 --stage-id 31 \
  --value ESTIMATED_VALUE
```

Deal title format: `{Project Name} - Painting` or `{Project Name} - Cleaning`
Tenders Clean = pipeline 3. Tenders Paint = pipeline 4. New deals start at QUOTE IN PROGRESS.

**4d** — Post pinned note with tender details (project ID, E1 link, brief summary, due date).

### Stage 5 — Attach documents

Create Google Drive folder, upload tender PDFs, link folder to deal.

### Stage 6 — Measure (if plans available)

If `brief.has_plans == true`: follow `eps/workflows/measure-floor-plan.md`.
No plans: use `areas_mentioned` from brief, or ask Allen.

### Stage 7 — Generate quote

Follow `eps/workflows/create-quote.md`. Output: quote_data.json > Google Doc > PDF.

### Gate 2 — Allen reviews quote

Present: total (inc GST), line items, doc link, flags (estimated dimensions, special conditions).

Ask: **Send? Revise? Adjust rates?**

### Stage 8 — Submit

- Move deal to QUOTE SENT stage
- Create follow-up activity (2 weeks out)
- Submit via E1 or email directly
- Post completion note: "Quote submitted [date]. Follow-up [date]. Total: $X,XXX inc GST."

---

## Builder lead flow (cold outreach)

For new builders found on E1 — separate from quoting:

```bash
python3 tools/pipedrive_create.py --action create-org --name "BUILDER_NAME" --address "LOCATION"
python3 tools/pipedrive_create.py --action create-person --name "CONTACT" --org-id ORG_ID --phone "PHONE"
python3 tools/pipedrive_create.py --action create-lead --title "BUILDER_NAME - E1 Builder" --org-id ORG_ID --person-id PERSON_ID
```

Leads go to Pipedrive Leads inbox for cold calling.

---

## Output format (after scraping)

```
E1 Scrape — [date]
Leads: X active (Y new since last run)
Open tenders: X with painting/cleaning scope
Sheet: [link]
```

If new leads, list: builder name + project title.

---

## Rules

- Load credentials from `eps/.env`
- Always search before creating CRM records (dedup)
- Never skip Gate 1 or Gate 2
- Post pinned note at each stage
- Flag estimated measurements in the quote
- Login failure: check screenshot in `.tmp/estimateone/`, retry once, then report
