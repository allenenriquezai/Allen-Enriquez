# Call Notes

Fetch a call transcript, format it, and post as a pinned note to the Pipedrive deal.

---

## Inputs

1. **Deal ID or client name**
2. **Call type** — discovery, follow-up, site visit, or general

---

## Steps

### Step 1 — Resolve deal ID (if only name given)

```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/search?term=CLIENT_NAME&api_token=${PIPEDRIVE_API_KEY}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(i['item']['id'], i['item']['title']) for i in d.get('data',{}).get('items',[])]"
```

### Step 2 — Fetch transcript (MANDATORY)

```bash
python3 tools/eps/fetch_call_transcript.py --deal-id DEAL_ID --call-type CALL_TYPE
```

Handle the status:
- `"ok"` — transcript in `.tmp/`, proceed to Step 3
- `"transcript_url"` — navigate to `iq_transcript_url` via Chrome MCP, read page text, write to `projects/eps/.tmp/transcript_DEAL_ID.txt`, proceed
- `"transcript_not_ready"` — STOP. Tell Allen to try again in a few minutes.

### Step 3 — Read the transcript

Read `projects/eps/.tmp/transcript_DEAL_ID.txt`.

### Step 4 — Format the note

Apply this template:

```
Client
Name:
Company:
Address:
Job Type:
____________________

TO DO
- Internal sales actions only (send quote, organise site visit, follow up, confirm measurements)
____________________

Scope
- Actual work only
- Painting: surfaces, areas, repairs, colours, access, inclusions
- Cleaning: rooms/areas, frequency, condition, inclusions
____________________

Project Breakdown
- ONLY if multiple components, buildings, units, stages, or separately measured parts
- One bullet per item with labels (Townhouse 1, Unit 2, Stage 1, etc.)
- Include quantities, sqm, hours per item
____________________

Pricing
- Rates discussed, hours/visits/quantities
- Mobilisation fees, totals, variation rates
- Budget comments, pricing reaction
____________________

Situation
- Why they are enquiring
- Current context at the property/project
____________________

Pains / Issues
- Problems, concerns, objections, frustrations
- Anything blocking the decision
____________________

Special Notes
- Decision process, referral source, client tone
- Priorities: quality, warranty, timing, price
____________________

Timing
- Start date, deadline, frequency, follow-up timing
- Dependencies on other works, approvals, tenants, trades
____________________
```

**Section rules:**
- TO DO = internal sales actions only
- Scope = actual work only — never merge with Situation
- Project Breakdown = only for complex/multi-part jobs
- Situation and Pains/Issues stay separate
- Preserve exact section order
- Do NOT add info not in the transcript. Leave blank sections with just the heading.
- Preserve all numbers, names, dates, phone numbers exactly.

**Discovery calls** — also extract: Address, Job Type, Date Of Service, Business Division, Quote Brief.

### Step 5 — Post as pinned note

```bash
source projects/eps/.env
python3 -c "
import json, urllib.request
content = '''FORMATTED_NOTE'''
payload = json.dumps({'content': content, 'deal_id': DEAL_ID, 'pinned_to_deal_flag': 1}).encode()
req = urllib.request.Request('https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/notes?api_token=${PIPEDRIVE_API_KEY}', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as r:
    resp = json.loads(r.read())
    print('Note posted' if resp.get('success') else f'ERROR: {resp}')
"
```

### Step 6 — Discovery calls only: update deal fields

Fetch current deal fields first, then update based on these rules:

| Field | Key | Rule |
|---|---|---|
| Address | `3f2f68c9d737558d5f02bbbe384e4bfab75bdf39` | Always overwrite |
| Job Type | `7a974b1ee68b84b0e997d512823acc26311d1a15` | Always overwrite |
| Date Of Service | `251557510b933c5e46667c15439d09e9ce4207db` | Only if blank |
| Business Division | `6f2701b7f1505b60653dd85450d8a5321f2f7a7e` | Only if blank |
| Quote Brief | `cb25df0d7fbc6da63daa6a50b1c161ae6579488e` | Only if blank |

**Job Type values:** Multiple Painting, Internal Painting, External Painting, Roof Painting, Fence Painting, Lead Paint Removal, Industrial Coating, 1-Stage Construction Clean

```bash
source projects/eps/.env
# Fetch current fields
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/DEAL_ID?api_token=${PIPEDRIVE_API_KEY}"

# Update (only fields with data + meeting update rules)
curl -s -X PUT "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/DEAL_ID?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{ FIELDS_TO_UPDATE }'
```

Also: fetch person > update phone/email if blank. Fetch org > update address if blank. No org linked > create one and link.

---

## Rules

- Load credentials from `eps/.env`
- Post note BEFORE updating fields — note is the priority
- Never change deal stage or send emails
- Keep output to Allen minimal: confirm note posted + list fields updated
