# CRM Ops Workflow

Common Pipedrive operations for EPS deals. Use the eps-crm-agent for execution.

## Credentials
Required in `projects/eps/.env`:
```
PIPEDRIVE_API_KEY=<key>
PIPEDRIVE_COMPANY_DOMAIN=<e.g. essentialpropertysolutionsptyltd.pipedrive.com>
PIPEDRIVE_FOLDER_FIELD_KEY=<hash for Quote Folder Link — used by update_pipedrive_deal.py>
PIPEDRIVE_DOC_FIELD_KEY=<hash for Draft Quote Doc Link — used by update_pipedrive_deal.py>
```
Base URL: `https://{PIPEDRIVE_COMPANY_DOMAIN}/api/v1`

## Key Field Keys

| Field | Key |
|---|---|
| Sm8 Job # | `052a8b8271d035ca4780f8ae06cd7b5370df544c` |
| Quote Folder Link | `04ed807860923fac89bedf563b1c5409e1f9e862` |
| Draft Quote Doc Link | `c031a16cda356f6371b724d40b4c8f7ddbb4e094` |

## Pipeline + Stage IDs (EPS only — pipelines 1 & 2)

| Pipeline | Account | Stage | Name |
|---|---|---|---|
| 1 | EPS Clean | 22 | NEW |
| 1 | EPS Clean | 3 | SITE VISIT |
| 1 | EPS Clean | 24 | QUOTE IN PROGRESS |
| 1 | EPS Clean | 4 | QUOTE SENT |
| 1 | EPS Clean | 18 | NEGOTIATION / FOLLOW UP |
| 1 | EPS Clean | 5 | LATE FOLLOW UP |
| 1 | EPS Clean | 47 | DEPOSIT PROCESS |
| 2 | EPS Paint | 21 | NEW |
| 2 | EPS Paint | 10 | SITE VISIT |
| 2 | EPS Paint | 27 | QUOTE IN PROGRESS |
| 2 | EPS Paint | 11 | QUOTE SENT |
| 2 | EPS Paint | 17 | NEGOTIATION / FOLLOW UP |
| 2 | EPS Paint | 12 | LATE FOLLOW UP |
| 2 | EPS Paint | 48 | DEPOSIT PROCESS |

---

## Operations

### Look up a deal
```
GET /deals/{id}?api_token={key}
```
Returns: title, stage_id, pipeline_id, person_id, org_id, custom fields.

### Search deals by name
```
GET /deals/search?term={name}&api_token={key}
```

### Get person (contact) on a deal
```
GET /persons/{person_id}?api_token={key}
```
Returns: name, email, phone.

### Move deal to a stage
```
PUT /deals/{id}?api_token={key}
Body: {"stage_id": <stage_id>}
```

### Update a custom field on a deal
```
PUT /deals/{id}?api_token={key}
Body: {"<field_key>": "<value>"}
```

### Post a note to a deal
```
POST /notes?api_token={key}
Body: {"content": "<text>", "deal_id": <id>, "pinned_to_deal_flag": 1}
```
Set `pinned_to_deal_flag: 1` to pin the note so it's visible at the top.

### List all stages (reference)
```
GET /stages?api_token={key}
```

---

## Rules
- Only operate on pipeline 1 (EPS Clean) and pipeline 2 (EPS Paint)
- Never delete deals or contacts
- When posting notes, always pin them (`pinned_to_deal_flag: 1`)
- Confirm stage moves with Allen before executing
