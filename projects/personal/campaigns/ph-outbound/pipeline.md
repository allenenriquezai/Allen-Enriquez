# PH Outbound — Pipeline

This file shows the stages. Live state lives in the PH Outreach Google Sheet.
Sheet ID: `15NvyLkAWya3ZNxT-R1dSPTVN1z2CyKEzDTdfxHY38Do`

Most of this runs on its own via `tools/outreach.py`.

## Stages

| # | Stage | What it means | Who moves it |
|---|---|---|---|
| 1 | Discovered | Prospect URL or biz pulled from a source. | Tool (Sunday discover run). |
| 2 | Enriched | Email, FB URL, Haiku personal hook filled in. | Tool (daily 6am). |
| 3 | Queued | Made it into today's queue file. | Tool (daily 6am). |
| 4 | Sent | Allen sent the message. Logged via `log-sent`. | Allen (manual). |
| 5 | No reply | 3+ days, no reply. Goes into follow-up. | Tool (auto follow-up). |
| 6 | Reply | They replied. Draft made. | Tool drafts, Allen sends. |
| 7 | Booked | Discovery call on the calendar. | Allen. |
| 8 | Closed | Paid or dead. | Allen. |

## Flow

```
Discovered
   |
   v
Enriched -- (bad data, no email) --> Drop
   |
   v
Queued
   |
   v
Sent
   |
   v
No reply -- (Touch 2 sent) --> still no reply --> Cold after 14 days
   |
   v
Reply
   |
   v
Booked -- (no show) --> Try once more, then drop.
   |
   v
Closed (paid or dead)
```

## Daily numbers

- 5 emails per day (after warm-up)
- 10 FB DMs per day (max 12)
- ~15 min Allen time

## Notes

- Discovery runs Sunday 3am.
- Enrich + queue + follow-up + reply poll runs daily 6am.
- Allen gets WhatsApp ping when queue is ready.
- Opt-out keywords auto-mark `do_not_contact`. Never re-contact.
