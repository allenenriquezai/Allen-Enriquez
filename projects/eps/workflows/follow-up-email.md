# EPS Follow-Up Email Workflow

Trigger: Allen asks to follow up with a client, OR a deal has been in "Quote Sent" for 3+ days with no response.

---

## Step 1 — Get Deal Info

If Allen provides a deal ID, use it directly.
If Allen provides a client name, search Pipedrive:
```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/v1/deals/search?term=CLIENT_NAME&api_token=${PIPEDRIVE_API_KEY}" | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['item']['id'], i['item']['title']) for i in d.get('data',{}).get('items',[])]"
```

Extract from the deal:
- Client first name + email
- Service type (from deal title or notes)
- Original quote total
- Date quote was sent
- Last activity date

---

## Step 2 — Choose Template

| Service type | Template key |
|---|---|
| Residential painting | `follow_ups/residential_painting` |
| Residential cleaning | `follow_ups/residential_cleaning` |
| Builders — cleaning | `follow_ups/builders_cleaning` |
| Builders — painting | `follow_ups/builders_painting` |

---

## Step 3 — Collect Inputs

Ask Allen (if not already known):
- **Opener** — 1-line reference to the original call or quote (e.g. "Hope the project is coming along well.")
- **Any new info** — anything that changed since the quote (price adjustment, availability, added bonus)

---

## Step 4 — Draft Follow-Up

```bash
python3 tools/draft_follow_up_email.py \
  --deal-id "DEAL_ID" \
  --template "follow_ups/<key>" \
  --first-name "NAME" \
  --to "email@example.com" \
  --opener "OPENER_LINE"
```

Add `--new-info "..."` if there's something new to mention.

---

## Step 5 — QA

Run eps-qa-agent:
```bash
# eps-qa-agent checks: no placeholders, under 120 words, tone match, preference alignment
# It posts the draft as a pinned note on the Pipedrive deal
```

---

## Step 6 — Allen Reviews in Pipedrive

Allen reviews the pinned note on the deal. If approved:

```bash
python3 tools/draft_follow_up_email.py \
  --deal-id "DEAL_ID" \
  --template "follow_ups/<key>" \
  --first-name "NAME" \
  --to "email@example.com" \
  --opener "OPENER_LINE" \
  --send
```

---

## Notes

- Follow-ups must be under 120 words — shorter than quote emails
- No pressure language — soft check-in only
- Builders tone: direct, professional, brief
- Residential tone: warm, reference their specific situation
- Do not resend the quote PDF — reference the original email instead
- If no response after a second follow-up, flag to Allen for a call
