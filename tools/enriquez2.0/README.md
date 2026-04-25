# Enriquez2.0

Knowledge + audit + opportunity engine. Filters world signal through Allen's identity, distills domain standards, audits reality vs standards, surfaces new moves to make. The "v2" of how Allen operates (v1 = manual + n8n era).

> **Architecture:** see [OVERVIEW.md](OVERVIEW.md) for the full data-flow diagram.
> **Systems index:** see [SYSTEMS.md](SYSTEMS.md) for an index of all tools across the repo.

## Domains
- **BUILD** — how we ship better (repo, Claude Code, automation)
- **REACH** — how we grow audience + clients (content, hooks, cadence)
- **SERVE** — how we turn audience into paid clients (offer, delivery, onboarding)

## Daily Loop
```
npm run ingest                       # pull sources → route → write inbox.md
# Allen reviews domains/<d>/inbox.md, marks `[promote]`
npm run distill -- --domain build    # promoted items roll into standard.md
npm run mirror                       # snapshot repo state to state/*.json
npm run audit -- --domain build      # gap report standard vs state
npm run opportunities                # surface NEW moves from inbox
npm run brief                        # daily 1-pager (inbox + audits + opportunities)
```

## Layout
- `identity/` — who Allen is + becoming. Hand-edited.
- `domains/<d>/sources.yaml` — RSS/Reddit/GitHub feeds per domain.
- `domains/<d>/inbox.md` — routed items pending review.
- `domains/<d>/standard.md` — current "what good looks like" per domain.
- `state/*.json` — snapshot of repo / content / automations.
- `audits/<d>-YYYY-MM-DD.md` — gap reports per domain.
- `opportunities/YYYY-MM-DD.md` — proposed new moves.
- `briefs/YYYY-MM-DD.md` — daily summaries.
- `raw/` — gitignored, raw ingestion output.

## Setup
```
cd tools/enriquez2.0
npm install
# Anthropic API key picked up from projects/personal/.env or projects/eps/.env
npm run ingest -- --domain build --since 7d
```

## Stack
TypeScript + tsx scripts. No DB, no Next.js. Markdown + JSON files only. Anthropic SDK (Haiku for routing, Sonnet for distill/audit/opportunities).
