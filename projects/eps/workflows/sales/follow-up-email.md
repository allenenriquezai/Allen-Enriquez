# Follow-Up Email

Send a follow-up to a client whose quote has gone quiet. Draft > QA > Allen approves > send.

---

## When to follow up

- Deal in "Quote Sent" for 3+ days with no response
- Allen explicitly asks

---

## Decision logic

| Situation | Action |
|---|---|
| Deal ID provided | Use it directly |
| Client name only | Search Pipedrive first: `curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/v1/deals/search?term=NAME&api_token=${PIPEDRIVE_API_KEY}"` |
| New info available | Add `--new-info "..."` to draft command |
| Already followed up once, no response | Ask Allen: "Second follow-up — flag for a call instead?" |
| After 2nd follow-up, no response | Flag for call. Do NOT send a 3rd email. |

---

## Template keys

| Service | Key |
|---|---|
| Residential painting | `follow_ups/residential_painting` |
| Residential cleaning | `follow_ups/residential_cleaning` |
| Builders — cleaning | `follow_ups/builders_cleaning` |
| Builders — painting | `follow_ups/builders_painting` |

Templates live in `eps/templates/email/follow_ups/`.

---

## Tone rules

- Soft check-in only. No pressure. No "just following up."
- Under 120 words. Simple English, 3rd grade reading level.
- One sentence per paragraph. Line breaks between.
- Residential = warm, reference their specific situation from the quote.
- Builders = direct, professional, brief. Reference company name.
- Do NOT resend the PDF.
- Sign-off always: `Allen @EPS Team`

---

## Final follow-up (quote expiring, no answer on calls)

```
[First name],

I tried calling but couldn't get through.

Your quote expires today.

Have you given up on this, or are you still looking for a [service]?

Happy to help if you are.

Allen @EPS Team
```

---

## Steps

### Step 1 — Get deal info (if not provided)

```bash
source projects/eps/.env
curl -s "https://${PIPEDRIVE_COMPANY_DOMAIN}/v1/deals/search?term=CLIENT_NAME&api_token=${PIPEDRIVE_API_KEY}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['item']['id'], i['item']['title']) for i in d.get('data',{}).get('items',[])]"
```

Extract: first name, email, service type, quote total, date sent, last activity.

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

### Step 3 — QA

Run QA per `eps/workflows/sales/qa.md` (SOP 2: Email). Checks:
- No unfilled `[placeholders]`
- Under 120 words
- Tone matches client type
- Subject line is specific
- No formatting artifacts

QA posts draft as pinned note on Pipedrive deal.

- FAILED: fix issues, re-draft. Do NOT show Allen.
- PASSED: show Allen the draft.

### Step 4 — Send (after Allen approves)

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

## Rules

- Draft first, always. Never send without QA + Allen approval.
- Load credentials from `eps/.env`.
- Nothing client-facing without QA passing.
- After sending, ask Allen for edits — save preferences to QA workflow.
