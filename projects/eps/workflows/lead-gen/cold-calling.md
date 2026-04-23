# Cold Calling

Batch processor for after a cold calling session. Fetch > format > draft emails > post.

**CRITICAL:** Never fabricate activity types. Only source of truth = batch JSON from `process_cold_calls.py fetch`.

---

## Steps

### Step 1 — Fetch the batch (MANDATORY)

```bash
python3 tools/eps/process_cold_calls.py fetch --verbose
```

If `count` is 0: "No recently called leads found." STOP.

You MUST run this step. Do not skip. Do not fabricate lead data.

### Step 2 — Read batch and filter

```bash
cat projects/eps/.tmp/cold_call_batch.json
```

Split into two groups:

**Connected (process these):**
- Not Interested
- Asked For Email
- Call Back
- Late Follow Up
- Warm Interest
- Converted To Deal

**Skip these:**
- No Answer 1/2/3
- Invalid Number

Tell Allen which leads are skipped and why.

### Step 3 — Format each connected lead's note

Apply this template:

```
Cold Call — {activity_type}
Company: {lead_title}
Contact: {person_name}
____________________

Notes
- {clean up raw note into bullets}
- {fix grammar, keep all details brief}
- {preserve names, numbers, dates exactly}
____________________

Next Step
- {auto-generate based on activity type}
____________________
```

**Next step rules:**

| Activity type | Next step |
|---|---|
| Not Interested / Not Qualified | No further action |
| Asked For Email | Send intro email |
| Call Back | Call back [date/time if mentioned] |
| Late Follow Up | Follow up later |
| Warm Interest | Send follow-up email + schedule callback |
| Converted To Deal | Create deal in Pipedrive |

### Step 4 — Draft emails (Asked For Email + Warm Interest only)

Only for leads where `needs_email` is `true`.

Template:

```
Subject: Painting & Cleaning for {company or person name}

Hi {first_name},

Good talking to you today.

{1-2 sentences based on what was discussed}

We help builders with:
- Painting — interior and exterior
- Post-construction cleaning
- Regular site cleans during build

{If Warm Interest: reference their specific interest from the note}

Happy to send more info or set up a quick chat.

Allen
EPS Painting & Cleaning
```

Rules: under 100 words, simple English (3rd-5th grade), professional proof-led, problem-focused, reference what was discussed.

### Step 5 — Write output and post

For each connected lead:

```bash
cat > projects/eps/.tmp/cold_call_lead_LEAD_ID.json << 'JSONEOF'
{
  "lead_id": "LEAD_ID",
  "lead_title": "TITLE",
  "person_id": PERSON_ID,
  "formatted_note": "THE_FORMATTED_NOTE",
  "email_draft": {
    "to": "EMAIL",
    "subject": "SUBJECT",
    "body": "BODY"
  }
}
JSONEOF

python3 tools/eps/process_cold_calls.py post --lead-id LEAD_ID
```

Omit `email_draft` if lead doesn't need one.

### Step 6 — Show ALL email drafts to Allen

Show every draft together. Do NOT auto-send. Wait for approval.

```
Email Drafts (X total)

--- Smith Builders (John) ---
To: john@example.com
Subject: ...
Body: ...

--- Next Company (Name) ---
...
```

### Step 7 — Print summary

```
=== Cold Call Batch Complete ===
Processed: X leads
  No Answer:        X
  Asked For Email:  X (emails drafted)
  Warm Interest:    X (emails drafted)
  Not Interested:   X
  Call Back:        X
  ...

X emails ready for review.
```

---

## Rules

- Load credentials from `eps/.env`
- Always run `process_cold_calls.py fetch` first — never skip, never fabricate
- Only post notes for connected leads — skip No Answer and Invalid Number
- Never update lead labels — JustCall dispositions handle that
- Never send emails — only draft
- Never create deals — Allen does that manually
- Preserve all numbers, names, dates, phone numbers exactly
- No raw_note on a lead: post note with just activity type + next step
- If anything looks wrong (e.g. all leads same activity type): STOP and flag to Allen
