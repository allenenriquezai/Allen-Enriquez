---
name: EPS Re-engagement Campaign
description: Re-engagement campaign structure — Pipedrive project boards, SM8 as source of truth, Google Sheet tracker, batch email workflow
type: project
---

Re-engagement campaign for EPS previous clients and lost deals.

**Tracking:**
- Google Sheet: https://docs.google.com/spreadsheets/d/1C4wE9KLKcZ_Ijmh9lzUPCNnc1vb3tTdi5nMOK8E_tY4
- Pipedrive Project Boards: Board 3 (Clean Re-engage), Board 5 (Paint Re-engage)
- Phases: New/For Review → Added to Sequence → Contact Made → Google Review Done → Interested/Cross-sell → Not Interested

**Source of truth:**
- Service dates/details: SM8 (not Pipedrive — won dates were bulk-marked and are inaccurate)
- Emails/activities: always on the person record (not project)

**Batch progress:**
- Batch 1 SENT (Apr 13): Alexandra Koek, Angelique Williams, Aziz Kahharov, Chris Brady, Diego Acero, Elese, Glen Winter
- Batches 2-4: ~37 clients remaining. Full list in `.tmp/reengage_emails_batch1.md`

**Skip list:** Azure Build, Quadric contacts, Paladin, Future Fitouts, Mercedes-Benz, Ethan Dooley, Ryan Haggerty/Audi, Brendan Joicey (active recurring), Antonios Chrysafinas (Future Fitouts contact), David Remy (not in SM8)
**Call only:** Joshua Marcinkewycz (turned off on service), Johnathon Louis/Conceptci (not responding)

**Why:** Tool + morning briefing integration. No new agent — complexity doesn't justify one yet.
**How to apply:** When resuming campaign work, read `.tmp/reengage_emails_batch1.md` for batch progress and `.tmp/reengage_enriched.json` for client data. Plan file at `.claude/plans/noble-beaming-wombat.md` has the automation script design.
