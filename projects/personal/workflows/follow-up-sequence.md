# Follow-Up Sequence — Personal Brand Cold Outreach

Automated follow-up for warm leads from cold-calling painting companies in Charlotte NC.

## Lead Sources (CRM Tabs to Monitor)

| Tab | Sequence |
|---|---|
| `Paint \| Warm Interest` | Full 3-touch |
| `Other \| Warm Interest` | Full 3-touch |
| `Paint \| Callbacks` | Single touch reminder |
| `Other \| Callbacks` | Single touch reminder |

## Timing Rules

| Touch | Trigger | Max Words |
|---|---|---|
| Touch 1 | Within 1 hour of warm call | 60 |
| Touch 2 | 48 hours after Touch 1, no reply | 40 |
| Touch 3 | 5 days after Touch 1, no reply | 50 |
| After Touch 3 | No reply → move to "Late Follow Up" tab | — |

For Callbacks tabs: send Touch 1 only. If no reply after 48h, move to Late Follow Up.

## Templates

### Touch 1 — Post-Call Personalized Email
**Subject:** Good talking with you, [firstName]

Hi [firstName],

Great chatting earlier about [businessName]. [callReference]

Here's a quick look at what we've done for similar companies: [caseStudyLink]

Happy to answer any questions.

— Allen

### Touch 2 — Soft Check-In (48h, no reply)
**Subject:** Re: Good talking with you, [firstName]

Hi [firstName],

Just wanted to make sure my last email landed. Would love to help [businessName] save time on the admin side.

Let me know if you have any questions.

— Allen

### Touch 3 — Last Touch with Value Add (5 days, no reply)
**Subject:** One more thought for [businessName]

Hi [firstName],

[callReference]

No worries if the timing isn't right — just wanted to share that in case it's useful.

— Allen

## Tracking Follow-Ups in CRM

After each email sent, append to the lead's `notes` field:
```
[FU1 sent 2026-04-09]
[FU2 sent 2026-04-11]
[FU3 sent 2026-04-14]
```

Before sending any touch:
1. Read the lead's `notes` field
2. Check if that touch was already sent (look for `[FUn sent ...]`)
3. Parse dates to verify timing gap has passed
4. Skip if already sent or timing not met

## QA Checks (Before Every Send)

- [ ] No unfilled placeholders (`[firstName]`, `[businessName]`, etc.)
- [ ] Word count within limit for the touch number
- [ ] Tone is casual and friendly (not salesy)
- [ ] Subject line is filled
- [ ] `to` email address is present and valid format

If any check fails, skip that lead and log the reason.

## How to Calculate Timing

1. **Touch 1 due?** → `date_called` exists AND no `[FU1 sent ...]` in notes AND within 24h of call
2. **Touch 2 due?** → `[FU1 sent DATE]` exists AND no `[FU2 sent ...]` AND today >= FU1 date + 48h
3. **Touch 3 due?** → `[FU1 sent DATE]` exists AND no `[FU3 sent ...]` AND today >= FU1 date + 5 days
4. **Done?** → `[FU3 sent ...]` exists AND today >= FU3 date + 48h → move to Late Follow Up

## Sending

Use the standalone email tool:
```bash
python3 tools/send_personal_email.py --to "EMAIL" --subject "SUBJECT" --body "BODY"
```

For dry runs (preview without sending):
```bash
python3 tools/send_personal_email.py --to "EMAIL" --subject "SUBJECT" --body "BODY" --dry-run
```

## Moving Leads to Late Follow Up

After Touch 3 with no reply (48h grace period):
1. Append `[Moved to Late Follow Up 2026-04-16]` to notes
2. Move the row to the appropriate Late Follow Up tab
3. Do NOT delete the original row — move only
