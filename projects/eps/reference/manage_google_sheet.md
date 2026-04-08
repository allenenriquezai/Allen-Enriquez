# Workflow: Manage Google Sheet

## Objective
Set up and manage the Charlotte NC Prospects Google Sheet.

## Spreadsheet
ID: `1Upp2lhiTeRsybaBHEy5_6FTBLcCN5fJ8l-TjpyqrGUs` (also in `projects/eps/.env`)

## Tools

### One-time setup (creates folder + sheet)
```
python tools/setup_sheet.py
```

### Append new prospects
```
python tools/append_prospects.py
```

### Bulk append pre-researched companies
```
python tools/append_painting_companies.py
```

### Overwrite entire sheet (destructive)
```
python tools/write_prospects.py
```

## Auth
- Requires `credentials.json` (OAuth client secrets) at project root
- `token.pickle` is cached after first login — delete to re-authenticate

## Columns
Business Name, Owner Name, Phone, Email, Website, City, Service Areas, Rating, Reviews, Owner LinkedIn, Facebook Page, Notes
