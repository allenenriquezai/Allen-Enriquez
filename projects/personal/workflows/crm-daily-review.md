# Workflow: Personal Brand CRM Daily Review

## Daily Rhythm

| Time (PH) | What | Command |
|---|---|---|
| ~6-7 PM | Evening briefing (priorities before calling) | `python3 tools/personal_crm.py evening-brief` |
| ~12:30 AM | Automated CRM cleanup (after calling) | Runs via launchd |

## Commands

### Evening Briefing
```
python3 tools/personal_crm.py evening-brief           # send email
python3 tools/personal_crm.py evening-brief --dry-run  # preview only
```
Scans CRM + personal Gmail + Calendar. Sends prioritised call list to allenenriquez006@gmail.com.

### CRM Cleanup (automated)
```
python3 tools/personal_crm.py cleanup           # run now
python3 tools/personal_crm.py cleanup --dry-run  # preview only
```
Normalises empty outcomes, fills follow-up dates from notes. Runs at 12:30 AM daily via launchd.

### Review (terminal)
```
python3 tools/personal_crm.py review
```
Quick terminal summary of hot leads, callbacks, and stats.

### Draft Email
```
python3 tools/personal_crm.py draft --row 3 --tab "Painting Companies"
```
Drafts outreach email for a specific lead. Auto-selects opener (cold/warm/asked-for-email).

### One-Time Cleanup
```
python3 tools/personal_crm.py clean --dry-run   # preview
python3 tools/personal_crm.py clean              # apply
```
Reorders columns, formats sheet, normalises data. Only needed once.

## launchd Setup

Install the cleanup schedule:
```
cp com.enriquezOS.personal-crm-cleanup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.enriquezOS.personal-crm-cleanup.plist
```

## Google Sheet
https://docs.google.com/spreadsheets/d/1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8

## Column Order (A-I = primary view)
Business Name | Decision Maker | Phone | Call Outcome | Notes | Follow-up Date | Date Called | Email | Website
