# Discovery Call — Deal Field Population

After posting the formatted note, update deal + person/org fields from transcript data.

## Deal custom fields

| Field | Key | Update rule |
|---|---|---|
| Address | `3f2f68c9d737558d5f02bbbe384e4bfab75bdf39` | Always overwrite |
| Job Type | `7a974b1ee68b84b0e997d512823acc26311d1a15` | Always overwrite |
| Date Of Service | `251557510b933c5e46667c15439d09e9ce4207db` | Only if blank |
| Business Division | `6f2701b7f1505b60653dd85450d8a5321f2f7a7e` | Only if blank |
| Quote Brief | `cb25df0d7fbc6da63daa6a50b1c161ae6579488e` | Only if blank |

**Job Type values:** Multiple Painting, Internal Painting, External Painting, Roof Painting, Fence Painting, Lead Paint Removal, Industrial Coating, 1-Stage Construction Clean

## Process

### 1. Fetch current deal fields
```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/DEAL_ID?api_token=${PIPEDRIVE_API_KEY}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
for key in ['3f2f68c9d737558d5f02bbbe384e4bfab75bdf39','7a974b1ee68b84b0e997d512823acc26311d1a15','251557510b933c5e46667c15439d09e9ce4207db','6f2701b7f1505b60653dd85450d8a5321f2f7a7e','cb25df0d7fbc6da63daa6a50b1c161ae6579488e']:
    print(f'{key}: {d.get(key)}')
"
```

### 2. Update deal (only fields with data + meeting update rules)
```bash
source projects/eps/.env
curl -s -X PUT "https://${PIPEDRIVE_COMPANY_DOMAIN}/api/v1/deals/DEAL_ID?api_token=${PIPEDRIVE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{ FIELDS_TO_UPDATE }'
```

### 3. Fill person/org blanks
- Fetch person → update phone/email if blank
- Fetch org → update address if blank
- If no org linked → create one and link to deal
