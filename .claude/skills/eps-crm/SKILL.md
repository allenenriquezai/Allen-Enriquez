---
name: eps-crm
description: EPS Pipedrive CRM — monitor pipeline, sync SM8, manage activities, search/create deals. Triggers on "EPS CRM", "pipeline report", "check deals", "sync CRM", "Pipedrive", or /eps-crm.
---

EPS Pipedrive CRM tool. Do NOT read any other files — everything you need is here.

## Pipelines
| ID | Name |
|---|---|
| 1 | EPS Clean |
| 2 | EPS Paint |
| 3 | Tenders - Clean |
| 4 | Tenders - Paint |

## Actions

Parse the user's request and run the matching command. If unclear, ask.

### monitor (default if no action specified)
```bash
python3 tools/crm_monitor.py --print
```
Pipeline scan — action items, KPIs, team scorecard. Print output directly.

For raw JSON (downstream use): `python3 tools/crm_monitor.py` → outputs to `.tmp/crm_monitor.json`.

### sync
```bash
python3 tools/crm_sync.py --dry-run --print   # preview first
python3 tools/crm_sync.py --print              # apply
```
Pipedrive <> SM8 reconciliation. Always dry-run first, show changes, ask before applying.

Sync a specific deal:
```bash
python3 tools/crm_sync.py --deal-id <ID> --dry-run --print
```

### activities
```bash
python3 tools/pipedrive_activities.py --print                          # today
python3 tools/pipedrive_activities.py --print --date 2026-04-17        # specific date
python3 tools/pipedrive_activities.py --print --subject "PREVIOUS"     # filter by subject
python3 tools/pipedrive_activities.py --print --done                   # completed only
python3 tools/pipedrive_activities.py --print --undone                 # pending only
```
Show activities. Always use `--print` for human-readable output.

### move-activities
```bash
python3 tools/pipedrive_activities.py --date <FROM> --subject "<FILTER>" --move-to <TO>
```
Bulk move filtered activities to new date. Show what will move first (run without `--move-to`), then confirm before moving.

### search
```bash
python3 tools/pipedrive_create.py --action search-org --name "<term>"
python3 tools/pipedrive_create.py --action search-person --name "<term>"
python3 tools/pipedrive_create.py --action search-deal --name "<term>"
```
Search orgs, persons, or deals. Infer entity type from context. If ambiguous, search all three.

### create
```bash
# Organization
python3 tools/pipedrive_create.py --action create-org --name "<name>" --address "<address>"

# Person (attach to org)
python3 tools/pipedrive_create.py --action create-person --name "<name>" --org-id <ID> --email "<email>" --phone "<phone>"

# Deal
python3 tools/pipedrive_create.py --action create-deal --title "<title>" --org-id <ID> --person-id <ID> --pipeline-id <ID> --stage-id <ID> --value <AUD>

# Lead
python3 tools/pipedrive_create.py --action create-lead --title "<title>" --org-id <ID> --person-id <ID> --expected-close-date "<YYYY-MM-DD>"
```
Always confirm entity details with user before creating. Orgs auto-deduplicate by name.

### update-deal
```bash
python3 tools/update_pipedrive_deal.py --deal-id "<ID>" --field folder --url "<drive_url>"
python3 tools/update_pipedrive_deal.py --deal-id "<ID>" --field doc --url "<drive_url>"
```
Update deal custom fields — quote folder link or draft quote doc link.

### stages
```bash
python3 tools/pipedrive_create.py --action list-stages --pipeline-id <ID>
```
List stages for a pipeline. Useful for confirming stage IDs before creating/moving deals.

## Rules
- Run commands from the repo root: `cd "/Users/allenenriquez/Developer/Allen-Enriquez"`
- Do NOT read tool source files — just run CLI commands
- Do NOT read memory files, CLAUDE.md, or workflow docs
- Suppress Python warnings: pipe through `2>&1 | grep -v Warning | grep -v warnings` for cleaner output
- If a command fails, THEN read the relevant section of the tool to debug
- Dry-run first for sync and move operations — always ask before applying
- Confirm with user before creating any entity (org, person, deal, lead)
