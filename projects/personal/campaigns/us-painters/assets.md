# US Painters — Assets

Everything built for this campaign. Use these. Don't rebuild.

## Sales assets

- **Lead magnet PDF** — `projects/personal/sales/lead-magnet.pdf`
  "5 things slowing down your sales." Send Day 0 after the call.

- **Landing page** — `projects/personal/landing-page/`
  Static HTML. Deploys free on GitHub Pages. See `landing-page/README.md`.

- **One-pager** — `projects/personal/sales/one-pager-quote-builder.pdf`
  Send when they ask "what exactly do you do?"

- **Follow-up sequence** — `projects/personal/sales/follow-up-sequence.md`
  4 emails. Day 0, 2, 5, 10. Reference copy.

- **Invoice template** — `projects/personal/sales/invoice-template.md`
  Send when they say yes.

- **Demo video script** — `projects/personal/sales/demo-video-script.md`
  90-second script. Allen records once. Reuse everywhere.

## Tools

- **Follow-up automation** — `tools/cold_call_followup.py`
  Tracks warm leads. Auto-sends Day 0, 2, 5, 10 emails with PDF.

## Data

- **Lead tracker** — `projects/personal/.tmp/cold_call_leads.json`
  Live state. Who is at what stage. Who replied. Who went cold.

## Before going live

Edit these (see `sales/README.md`):
- `tools/cold_call_followup.py` — set `CALENDAR_LINK` and `DEMO_VIDEO_LINK`
- `lead-magnet.pdf` — rebuild from `build_lead_magnet.py` with real link
- `one-pager-quote-builder.pdf` — rebuild from `build_one_pager.py` with real link
- `landing-page/index.html` — same calendar link
