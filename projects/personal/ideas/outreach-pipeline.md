# Automated Outreach Pipeline

**Status:** Next to build (after calling sessions validate the Sheet workflow)

## Phase 1 — Enrich (build first)
- Pull leads from Sheet that have a business name but missing info
- For each lead, scrape/search:
  - Email address (if missing)
  - LinkedIn profile URL
  - Facebook page
  - Something personal/specific about the owner (recent post, project, award, community involvement)
- Store ALL enrichment back into the Google Sheet (new columns: LinkedIn, Facebook, Personal Hook)
- No emails sent — just data collection
- Run in batches, review quality before moving to Phase 2

## Phase 2 — Campaign (build after Phase 1 data is validated)
- Pull enriched leads with emails + personal hooks
- Draft personalised emails referencing the personal hook
- Cap at 5/day, staggered send times
- Track sends per lead in Sheet
- Max 2-3 touches per person without a reply
- Unsubscribe link in every email
- launchd schedule for daily sends

## Why two phases
Get the enrichment numbers right first. If the scraping quality is bad, fix it before burning leads with weak emails.

## Estimate
- Phase 1: ~1 session
- Phase 2: ~1 session
