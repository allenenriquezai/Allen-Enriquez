
# EPS CRM Operations

Read and write Pipedrive data for EPS deals. Fetch deal info, update fields, move stages, post notes.

---

## How to Work

1. Load credentials from `projects/eps/.env`
2. Read this file for API patterns, pipeline/stage IDs, and field keys
3. Execute the task using curl or the tools below
4. Return only what's needed — no raw JSON dumps

### Key Paths
- Env: `projects/eps/.env`
- Update tool: `tools/eps/update_pipedrive_deal.py`
- Create tool: `tools/eps/pipedrive_create.py` (orgs, persons, deals, leads)

---

## Domain Knowledge

### Credentials
Load from `projects/eps/.env`:
- `PIPEDRIVE_API_KEY`
- `PIPEDRIVE_COMPANY_DOMAIN` (e.g. `essentialpropertysolutionsptyltd.pipedrive.com`)

Base URL: `https://${PIPEDRIVE_COMPANY_DOMAIN}/v1`

### EPS pipelines
| Pipeline | Account |
|---|---|
| 1 | EPS Clean |
| 2 | EPS Paint |
| 3 | Tenders - Clean |
| 4 | Tenders - Paint |

Never touch pipelines outside this list.

### Stage IDs
| Pipeline | Stage name | Stage ID |
|---|---|---|
| 1 EPS Clean | NEW | 22 |
| 1 EPS Clean | SITE VISIT | 3 |
| 1 EPS Clean | QUOTE IN PROGRESS | 24 |
| 1 EPS Clean | QUOTE SENT | 4 |
| 1 EPS Clean | NEGOTIATION / FOLLOW UP | 18 |
| 1 EPS Clean | LATE FOLLOW UP | 5 |
| 1 EPS Clean | DEPOSIT PROCESS | 47 |
| 2 EPS Paint | NEW | 21 |
| 2 EPS Paint | SITE VISIT | 10 |
| 2 EPS Paint | QUOTE IN PROGRESS | 27 |
| 2 EPS Paint | QUOTE SENT | 11 |
| 2 EPS Paint | NEGOTIATION / FOLLOW UP | 17 |
| 2 EPS Paint | LATE FOLLOW UP | 12 |
| 2 EPS Paint | DEPOSIT PROCESS | 48 |

### Tender Pipeline Stage IDs

| Pipeline | Stage name | Stage ID |
|---|---|---|
| 3 Tenders - Clean | QUOTE IN PROGRESS | 31 |
| 3 Tenders - Clean | QUOTE SENT | 57 |
| 3 Tenders - Clean | FOLLOW UP | 58 |
| 3 Tenders - Clean | CONTACT MADE | 32 |
| 3 Tenders - Clean | NEGOTIATION / FOLLOW UP | 33 |
| 3 Tenders - Clean | LATE FOLLOW UP | 34 |
| 4 Tenders - Paint | QUOTE IN PROGRESS | 35 |
| 4 Tenders - Paint | QUOTE SENT | 59 |
| 4 Tenders - Paint | FOLLOW UP | 60 |
| 4 Tenders - Paint | CONTACT MADE | 36 |
| 4 Tenders - Paint | NEGOTIATION / FOLLOW UP | 37 |
| 4 Tenders - Paint | LATE FOLLOW UP | 38 |

### Projects Boards & Phases

| Board | Name | Phase ID | Phase Name |
|---|---|---|---|
| 1 | EPS Clean Projects | 35 | Recurring Active |
| 1 | EPS Clean Projects | 36 | New |
| 1 | EPS Clean Projects | 3 | Pending Booking |
| 1 | EPS Clean Projects | 4 | Booked |
| 1 | EPS Clean Projects | 5 | Fixups |
| 1 | EPS Clean Projects | 1 | Completed |
| 1 | EPS Clean Projects | 27 | Variations |
| 1 | EPS Clean Projects | 6 | Final Invoice |
| 2 | EPS Paint Projects | 37 | New |
| 2 | EPS Paint Projects | 8 | Pending Booking |
| 2 | EPS Paint Projects | 9 | Booked |
| 2 | EPS Paint Projects | 10 | Fix Ups |
| 2 | EPS Paint Projects | 11 | Completed |
| 2 | EPS Paint Projects | 12 | Variations |
| 2 | EPS Paint Projects | 25 | Final Invoice |
| 2 | EPS Paint Projects | 26 | Forward to Google Review |
| 3 | Clean Re-engagement | 13 | New / For Review |
| 3 | Clean Re-engagement | 14 | Added to Sequence |
| 3 | Clean Re-engagement | 15 | Contact Made / Responded |
| 3 | Clean Re-engagement | 16 | Google Review Done |
| 3 | Clean Re-engagement | 17 | Interested / Cross-sell |
| 3 | Clean Re-engagement | 28 | Not Interested |
| 5 | Paint Re-engagement | 29 | New / For Review |
| 5 | Paint Re-engagement | 30 | Added to Sequence |
| 5 | Paint Re-engagement | 31 | Contact Made / Responded |
| 5 | Paint Re-engagement | 32 | Google Review Done |
| 5 | Paint Re-engagement | 33 | Interested / Cross-sell |
| 5 | Paint Re-engagement | 34 | Not Interested |

### Custom field keys
| Field | Key |
|---|---|
| SM8 Job # | `052a8b8271d035ca4780f8ae06cd7b5370df544c` |
| Quote Folder Link | `04ed807860923fac89bedf563b1c5409e1f9e862` |
| Draft Quote Doc Link | `c031a16cda356f6371b724d40b4c8f7ddbb4e094` |
| Business Division | `6f2701b7f1505b60653dd85450d8a5321f2f7a7e` (enum: 56=EPS Clean, 57=EPS Paint) |

### Notes are always pinned
Always set `"pinned_to_deal_flag": 1` when posting notes.

---

## What to Return

When reading a deal, extract and return:
- Client name + email
- Deal title + stage name
- Deal value
- Last activity date
- SM8 job # (if populated)
- Quote doc link (if populated)
- Any pinned notes relevant to the task

Do not dump raw JSON — extract only what's needed.

---

## Decision Logic

| Situation | Action |
|---|---|
| Deal ID known | Fetch directly with GET /deals/{id} |
| Client name only | Search first: GET /deals/search?term=NAME |
| Stage move requested | Confirm the target stage with Allen before executing |
| Note posting requested | Confirm the note content before posting |
| Updating doc/folder URL | Use `update_pipedrive_deal.py` shortcut |
| Deal not in pipeline 1 or 2 | Stop — do not operate on it |

---

## API Operations

### Look up deal by ID
```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${PIPEDRIVE_API_KEY}" | python3 -m json.tool
```

### Search deals by name
```bash
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/search?term=CLIENT_NAME&api_token=${PIPEDRIVE_API_KEY}" | python3 -m json.tool
```

### Get contact (person) on a deal
```bash
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/persons/${PERSON_ID}?api_token=${PIPEDRIVE_API_KEY}" | python3 -m json.tool
```

### Move deal to a stage
```bash
curl -s -X PUT "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"stage_id": STAGE_ID}'
```

### Update a custom field
```bash
curl -s -X PUT "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"FIELD_KEY": "VALUE"}'
```

### Post a pinned note
```bash
curl -s -X POST "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/notes?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"content": "NOTE_TEXT", "deal_id": DEAL_ID, "pinned_to_deal_flag": 1}'
```

### Shortcut: update doc or folder URL
```bash
python3 tools/eps/update_pipedrive_deal.py --deal-id "DEAL_ID" --field doc|folder --url "URL"
```

### Create organization, person, deal, or lead
```bash
python3 tools/eps/pipedrive_create.py --action create-org --name "Builder Name" --address "Brisbane QLD"
python3 tools/eps/pipedrive_create.py --action create-person --name "Contact" --org-id ORG_ID --phone "PHONE"
python3 tools/eps/pipedrive_create.py --action create-deal --title "Project - Painting" --org-id ORG_ID --pipeline-id 4 --stage-id STAGE_ID
python3 tools/eps/pipedrive_create.py --action create-lead --title "Builder - Cold Call" --org-id ORG_ID
```

Organization creation auto-deduplicates by normalized name.

---

## Rules

- Never hardcode API keys — always load credentials from `.env`
- If deal ID is unknown, search by client name first
- Never delete deals or contacts
- Never modify deal stage without Allen's confirmation
- Never post a note without confirming content first
- Notes are always pinned (`pinned_to_deal_flag: 1`)
- Create tool auto-deduplicates organizations by name
