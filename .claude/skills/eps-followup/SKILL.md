---
name: eps-followup
description: Use when sending a follow-up email to an EPS client or lead. Triggered by phrases like "follow up", "follow-up email", "chase the client", "send a follow up".
disable-model-invocation: true
---

# EPS Follow-Up Skill

Send a follow-up email to a client whose quote has gone quiet. Draft → QA → Allen approves → send.

---

## Domain Knowledge

### When to follow up
- Deal has been in "Quote Sent" for 3+ days with no response
- Allen explicitly asks to follow up

### Tone rules — non-negotiable
- **Soft check-in only.** No pressure, no urgency, no "just following up" clichés.
- **Under 120 words** — shorter than quote emails.
- **Residential:** warm, reference their specific situation from the quote.
- **Builders:** direct, professional, brief. Reference company name if known.
- Do NOT resend the PDF — reference the original email instead.
- If no response after a second follow-up: flag to Allen for a call, do not send a third email.

### Template selection
| Service type | Template key |
|---|---|
| Residential painting | `follow_ups/residential_painting` |
| Residential cleaning | `follow_ups/residential_cleaning` |
| Builders — cleaning | `follow_ups/builders_cleaning` |
| Builders — painting | `follow_ups/builders_painting` |

Templates live in `projects/eps/templates/email/follow_ups/`.

---

## Decision Logic

| Situation | Action |
|---|---|
| Deal ID provided | Use it directly |
| Client name only | Search Pipedrive first to get deal ID, email, and service type |
| New info available (price, availability, bonus) | Add `--new-info "..."` to the draft command |
| Already followed up once, no response | Ask Allen: "This is the second follow-up — want me to flag it for a call instead?" |
| Template key unclear from deal | Ask Allen: residential or builder? painting or cleaning? |

---

## Steps

### Step 1 — Get deal info (if not provided)
```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/v1/deals/search?term=CLIENT_NAME&api_token=${PIPEDRIVE_API_KEY}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['item']['id'], i['item']['title']) for i in d.get('data',{}).get('items',[])]"
```
Extract: client first name, email, service type, quote total, date sent, last activity.

### Step 2 — Draft (no send)
```bash
python3 tools/draft_follow_up_email.py \
  --deal-id "DEAL_ID" \
  --template "follow_ups/<key>" \
  --first-name "NAME" \
  --to "email@example.com" \
  --opener "OPENER_LINE" \
  [--new-info "..."]
```

### Step 3 — QA via eps-qa-agent
eps-qa-agent checks:
- No unfilled `[placeholders]`
- Under 120 words
- Tone matches client type
- Subject line is specific
- No formatting artefacts
- Aligned with saved preferences

QA posts the draft as a pinned note on the Pipedrive deal.

### Step 4 — Allen reviews in Pipedrive
After approval:
```bash
python3 tools/draft_follow_up_email.py \
  --deal-id "DEAL_ID" \
  --template "follow_ups/<key>" \
  --first-name "NAME" \
  --to "email@example.com" \
  --opener "OPENER_LINE" \
  [--new-info "..."] \
  --send
```

---

## Success Criteria

- Draft passes QA (under 120 words, no placeholders, right tone)
- QA report + draft posted as pinned note on Pipedrive deal
- Allen has approved before `--send` is added
- Email sent via Gmail API (`sales@epsolution.com.au`)

---

## Full workflow reference
`projects/eps/workflows/follow-up-email.md`
