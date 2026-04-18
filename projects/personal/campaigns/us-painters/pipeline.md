# US Painters — Pipeline

This file shows the stages. Live data lives in `projects/personal/.tmp/cold_call_leads.json`.

## Stages

| # | Stage | What it means | Next move |
|---|---|---|---|
| 1 | Cold call | First call made. No interest yet. | Move on or try again later. |
| 2 | Warm interest | They want to see more. Asked for info. | Send Day 0 email + lead magnet PDF. |
| 3 | PDF sent | Email landed. PDF attached. | Wait for reply or Day 2 follow-up. |
| 4 | Follow-up active | In the 4-email sequence. | Tool sends Day 2, 5, 10. |
| 5 | Demo booked | Calendar booking made. | Run the demo. Send one-pager. |
| 6 | Paid setup | They said yes. Invoice sent. | Build the quote builder in 72 hours. |
| 7 | Live | System is running for them. | Check in week 1. Confirm it works. |
| 8 | Expansion | Quote builder works. They want more. | Pitch speed-to-lead, then full stack. |

## Flow

```
Cold call
   |
   v
Warm interest -- (no interest) --> Drop or retry
   |
   v
PDF sent
   |
   v
Follow-up active -- (no reply by Day 10) --> Cold. Move on.
   |
   v
Demo booked -- (no show) --> Try once more, then drop.
   |
   v
Paid setup
   |
   v
Live
   |
   v
Expansion
```

## Notes

- Tool moves leads through stages 2 to 4 on its own. Stages 5 to 8 are manual.
- Don't pitch full stack at the start. Land with quote builder. Trust first.
- If they go cold at stage 4, do not chase. Move on. Add back to list in 90 days.
