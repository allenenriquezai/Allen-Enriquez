# Sales Assets — Cold Call Conversion Stack

Built April 2026 to plug the leak between cold calls and booked meetings.

## Files

| File | What | When to use |
|---|---|---|
| `lead-magnet.pdf` | "5 things slowing down your sales" 1-page PDF | Attach to Day 0 follow-up email |
| `build_lead_magnet.py` | Regenerates the PDF | Run after editing copy |
| `one-pager-quote-builder.pdf` | Single-page sales sheet | Send when prospect asks "what exactly do you do?" |
| `build_one_pager.py` | Regenerates the one-pager | Run after editing copy |
| `follow-up-sequence.md` | The 4-email cold call follow-up sequence (text reference) | For manual sends or to edit copy in script |
| `invoice-template.md` | Invoice template for setup work | Send when they say yes |
| `demo-video-script.md` | 90-second demo video script | Allen records once, reuses everywhere |

## Tools

| Tool | Purpose |
|---|---|
| `tools/personal/cold_call_followup.py` | Tracks warm leads + auto-sends Day 0/2/5/10 emails with PDF attached |

## Daily workflow

1. After cold call → `python3 tools/personal/cold_call_followup.py add --first-name "Mike" --company "Mike's Painting" --email mike@... --pain "slow quotes" --send-day0 --send`
2. Cron daily run → `python3 tools/personal/cold_call_followup.py run --send`
3. When they reply → `python3 tools/personal/cold_call_followup.py reply --email mike@...`

## Before going live

Edit these in `tools/personal/cold_call_followup.py`:
- `CALENDAR_LINK` — real Google Calendar booking URL
- `DEMO_VIDEO_LINK` — real Loom/YT link once recorded

And in:
- `lead-magnet.pdf` (rebuild from `build_lead_magnet.py`) — replace `calendar.app.google/your-link-here`
- `one-pager-quote-builder.pdf` (rebuild from `build_one_pager.py`) — same calendar link
- `landing-page/index.html` — same calendar link

## Landing page

Lives at `projects/personal/landing-page/`. See `landing-page/README.md` for deploy steps.
