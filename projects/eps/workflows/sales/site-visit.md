# Site Visit

Schedule an SM8 site inspection for an EPS deal.

---

## Key paths

- Credentials: `projects/eps/.env`
- Tool: `tools/schedule_sm8_visit.py`
- Pipeline reference: `eps/workflows/operations/crm-ops.md`

---

## Steps

### Step 1 — Load credentials and fetch deal

```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${PIPEDRIVE_API_KEY}" | python3 -c "
import json,sys; d=json.load(sys.stdin)['data']
print(f'Title: {d[\"title\"]}')
print(f'Pipeline: {d[\"pipeline_id\"]}')
print(f'Stage: {d[\"stage_id\"]}')
"
```

### Step 2 — Check SM8 for linked job card

```bash
python3 -c "
import sys; sys.path.insert(0,'tools')
from schedule_sm8_visit import find_sm8_job_by_deal
job, pipeline = find_sm8_job_by_deal('${DEAL_ID}')
if job: print(f'FOUND|{job[\"generated_job_id\"]}|{pipeline}|{job[\"uuid\"]}')
else: print('NOT_FOUND')
"
```

- FOUND: skip to Step 3b
- NOT_FOUND: continue to Step 3a

### Step 3a — Move deal to Site Visit + wait for n8n

**Pipeline mapping:**

| Current pipeline_id | PUT body |
|---|---|
| 1 (EPS Clean) | `{"stage_id": 3}` |
| 2 (EPS Paint) | `{"stage_id": 10}` |
| 3 (Tenders Clean) | `{"pipeline_id": 1, "stage_id": 3}` |
| 4 (Tenders Paint) | `{"pipeline_id": 2, "stage_id": 10}` |

Already at Site Visit (stage 3 for pipeline 1, stage 10 for pipeline 2): skip the move.
Pipeline not 1-4: STOP. Tell Allen not supported.

```bash
curl -s -X PUT "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '${PUT_BODY}'
```

Always send both `pipeline_id` and `stage_id` together when switching pipelines.

**Poll for SM8 job card:** Re-run Step 2 check. If NOT_FOUND, wait 15s and retry. Max 4 retries (~1 min).

Still NOT_FOUND after 4 retries: "SM8 job card hasn't appeared. Check n8n execution history." STOP.

### Step 3b — Push scope to SM8

Fetch deal notes:

```bash
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/${DEAL_ID}/notes?api_token=${PIPEDRIVE_API_KEY}&sort=add_time%20DESC&limit=10" \
  | python3 -c "
import json,sys,re
data = json.load(sys.stdin).get('data') or []
for n in data:
    clean = re.sub(r'<[^>]+>', '\n', n.get('content','')).strip()
    print(clean)
    print('---')
"
```

Extract a **site visit brief** for SM8 job description:
- **Client** — name, company, phone
- **Address** — full site address
- **Scope** — what work is needed
- **Special notes** — access, timing, constraints
- **Pains / issues** — client concerns

Keep concise (~500 words max). Plain text. No emojis.
No notes on deal: use deal title as description.

Push to SM8:

```bash
python3 -c "
import sys, json; sys.path.insert(0,'tools')
from schedule_sm8_visit import sm8_get, SM8_KEYS
from requests import put

api_key = SM8_KEYS['${PIPELINE}']
description = '''${SITE_VISIT_BRIEF}'''
r = put(f'https://api.servicem8.com/api_1.0/job/${JOB_UUID}.json',
    headers={'X-API-Key': api_key, 'Content-Type': 'application/json'},
    json={'job_description': description})
print('Updated' if r.ok else f'ERROR: {r.status_code} {r.text}')
"
```

### Step 4 — Check calendars and suggest slots

```bash
python3 tools/schedule_sm8_visit.py --deal-id ${DEAL_ID} --date ${DATE} --staff ${STAFF} --check-only
```

Present to Allen:
- Full calendar view (SM8 Paint + SM8 Clean + Google Calendar)
- Top 3 recommended slots
- Ask Allen to pick

**Always show calendar before booking** — even if Allen gave date + time upfront.

### Step 5 — Book the visit

```bash
python3 tools/schedule_sm8_visit.py --deal-id ${DEAL_ID} --date ${DATE} --time ${HH_MM} --staff ${STAFF}
```

Report: job ID, staff, date, time, activity UUID.

---

## Rules

- Google Calendar is READ-ONLY. Never write to it.
- Default staff: Giovanni. Allen can override.
- Default duration: 60 min. Allen can override.
- Never fabricate calendar data. Always run the tool.
- Load credentials from `eps/.env`.
