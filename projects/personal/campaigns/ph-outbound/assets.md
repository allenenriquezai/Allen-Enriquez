# PH Outbound — Assets

What is built. What is missing. Where things live.

## Built

- **DM and email templates** — `projects/personal/templates/outreach/`
  12 files. 2 niches × 2 channels × 3 variants.

- **Workflow doc** — `projects/personal/workflows/sales/ph-outreach-system.md`
  Full system: setup, daily flow, weekly flow, CLI commands.

- **Config** — `projects/personal/reference/outreach_config.yaml`
  Limits, segments, pain points.

- **Tool** — `tools/outreach.py`
  Main CLI. Commands: discover, enrich, queue, log-sent, followups, replies, stats.

- **Sheet (CRM)** — `15NvyLkAWya3ZNxT-R1dSPTVN1z2CyKEzDTdfxHY38Do`
  Name: "PH Outreach". Live prospect tracker.

- **Daily queue file** — `projects/personal/.tmp/outreach_queue_YYYY-MM-DD.md`
  Generated at 6am daily. Allen reviews, sends, then runs `log-sent`.

## Missing — TBD

- **Lead magnets per niche** — TBD. Need 1 PDF per niche (VA, recruitment, realtor).
- **Dedicated PH landing page** — TBD. US painter landing page won't fit PH market.
- **Pricing page or order link** — TBD. Tied to offer being locked.
- **Demo videos per niche** — TBD. US demo won't translate.

## Notes

- Send stays manual. No auto-send. Platform ban risk on FB and IG.
- Tool builds the queue. Allen sends from Gmail and FB. Then runs `log-sent`.
- Email warm-up: week 1 = 3/day, week 2 = 5, week 3 = 8, week 4 = 10, then 15 cap.
- FB DM cap: 12/day hard limit.
