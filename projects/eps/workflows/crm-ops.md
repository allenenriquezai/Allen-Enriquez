
# EPS CRM Skill

Read and write Pipedrive data for EPS deals. Fetch deal info, update fields, move stages, post notes.

---

## Domain Knowledge

### Credentials
Load from `projects/eps/.env`:
- `PIPEDRIVE_API_KEY`
- `PIPEDRIVE_COMPANY_DOMAIN` (e.g. `essentialpropertysolutionsptyltd.pipedrive.com`)

Base URL: `https://${PIPEDRIVE_COMPANY_DOMAIN}/v1`

### Only operate on EPS pipelines
| Pipeline | Account |
|---|---|
| 1 | EPS Clean |
| 2 | EPS Paint |

Never touch other pipelines.

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

### Custom field keys
| Field | Key |
|---|---|
| SM8 Job # | `052a8b8271d035ca4780f8ae06cd7b5370df544c` |
| Quote Folder Link | `04ed807860923fac89bedf563b1c5409e1f9e862` |
| Draft Quote Doc Link | `c031a16cda356f6371b724d40b4c8f7ddbb4e094` |

### Notes are always pinned
Always set `"pinned_to_deal_flag": 1` when posting notes.

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
python3 tools/update_pipedrive_deal.py --deal-id "DEAL_ID" --field doc|folder --url "URL"
```

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

## Rules

- Never delete deals or contacts
- Never modify stage without Allen's confirmation
- Never post a note without confirming content first
- Always load credentials from `.env` — never hardcode keys

