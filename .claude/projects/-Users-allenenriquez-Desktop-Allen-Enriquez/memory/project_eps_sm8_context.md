---
name: SM8 Job Context
description: SM8 jobs only exist for site-visited deals. Job cart and E1 tender deals skip SM8. Recurring clients have multiple SM8 jobs.
type: project
---

Not every Pipedrive deal has an SM8 job. SM8 jobs are only created when a site visit happens (via n8n automation). Deals from the job cart (Harold's team) or EstimateOne tenders go straight to quoting without SM8.

**Why:** Harold's team uses the job cart to create deals in Pipedrive for Allen to follow up. These are quote-and-follow-up only — no site visit, no SM8 job.

**How to apply:** Don't flag missing SM8 for deals in QUOTE SENT, NEGOTIATION, or LATE FOLLOW UP. Only flag missing SM8 for DEPOSIT PROCESS stage — by that point a job should exist. Recurring clients create separate SM8 jobs per visit, not one job per client.
