# Follow-Up Sequence SOP

Automated follow-up for warm leads from cold-calling painting companies (Charlotte NC) and general outreach.

## Lead Sources (CRM Tabs to Monitor)

| Tab | Sequence |
|---|---|
| `Paint \| Warm Interest` | Full 3-touch |
| `Other \| Warm Interest` | Full 3-touch |
| `Paint \| Callbacks` | Single touch only |
| `Other \| Callbacks` | Single touch only |

## Timing Rules

| Touch | Trigger | Max Words |
|---|---|---|
| Touch 1 | Within 1 hour of warm call | 60 |
| Touch 2 | 48h after Touch 1, no reply | 40 |
| Touch 3 | 5 days after Touch 1, no reply | 50 |
| After Touch 3 | No reply 48h+ after Touch 3 | Move to Late Follow Up |

Callbacks tabs: Touch 1 only. No reply after 48h = move to Late Follow Up.

## Templates

### Touch 1 -- Post-Call Email
**Subject:** Good talking with you, [firstName]

> Hi [firstName],
> Great chatting earlier about [businessName]. [callReference]
> Here's a quick look at what we've done for similar companies: [caseStudyLink]
> Happy to answer any questions.
> -- Allen

### Touch 2 -- Soft Check-In (48h, no reply)
**Subject:** Re: Good talking with you, [firstName]

> Hi [firstName],
> Just wanted to make sure my last email landed. Would love to help [businessName] save time on the admin side.
> Let me know if you have any questions.
> -- Allen

### Touch 3 -- Last Touch (5 days, no reply)
**Subject:** One more thought for [businessName]

> Hi [firstName],
> [callReference]
> No worries if the timing isn't right -- just wanted to share that in case it's useful.
> -- Allen

## Process

### Step 1 -- Load CRM
```bash
python3 tools/personal/personal_crm.py review
```
Fallback: read `.tmp/personal_crm.json`.

### Step 2 -- Identify Due Follow-Ups
For each lead in monitored tabs:
1. Read `notes` field for existing tags (`[FU1 sent ...]`, `[FU2 sent ...]`, `[FU3 sent ...]`)
2. Read `date_called` for Touch 1 timing
3. Calculate which touch is due:
   - Touch 1 due: `date_called` exists, no `[FU1 sent]`, within 24h
   - Touch 2 due: `[FU1 sent DATE]` exists, no `[FU2 sent]`, today >= FU1 + 48h
   - Touch 3 due: `[FU1 sent DATE]` exists, no `[FU3 sent]`, today >= FU1 + 5 days
   - Done: `[FU3 sent]` exists, today >= FU3 + 48h = move to Late Follow Up

### Step 3 -- Draft Emails
Fill all placeholders. If `callReference` can't be filled from notes, use a generic line. Default `caseStudyLink`: `https://allenenriquez.com/case-studies`

### Step 4 -- QA Before Send
- [ ] No unfilled placeholders
- [ ] Word count within limit
- [ ] Casual and friendly tone
- [ ] Subject line filled
- [ ] Valid email address

Skip and log if any check fails.

### Step 5 -- Send
**Batch mode (2+ emails):** Show Allen all drafts first. Wait for approval.
**Single/automation mode:** Send directly.

```bash
python3 tools/personal/send_personal_email.py --to "EMAIL" --subject "SUBJECT" --body "BODY"
python3 tools/personal/send_personal_email.py --to "EMAIL" --subject "SUBJECT" --body "BODY" --dry-run  # preview
```

### Step 6 -- Update CRM
After each send:
```bash
python3 tools/personal/personal_crm.py update-note --tab "TAB_NAME" --row ROW_NUM --append "[FU1 sent YYYY-MM-DD]"
```

### Step 7 -- Move Completed Leads
Touch 3 sent + 48h no reply:
1. Append `[Moved to Late Follow Up YYYY-MM-DD]` to notes
2. Move to Late Follow Up tab
3. Do NOT delete the original row

### Step 8 -- Log
Write to `.tmp/followup_log.json`:
```json
{
  "run_date": "YYYY-MM-DD HH:MM",
  "emails_sent": 2,
  "leads_moved_to_late": 1,
  "skipped": 3,
  "details": [
    {"lead": "Chris @ ABC Painting", "action": "FU1 sent", "email": "chris@abc.com"}
  ]
}
```

Print summary: X emails sent (names + touch number), X moved to Late Follow Up, X skipped (with reasons).

## Rules

- NEVER send without verifying timing. No duplicate sends within 48h.
- NEVER send if any placeholder is unfilled. Skip and log.
- Maximum 3 emails total per lead across the entire sequence.
- NEVER fabricate call details.
- In batch mode, always show drafts to Allen before sending.
- If no email address, skip and flag.
- All actions logged to `.tmp/followup_log.json`.
