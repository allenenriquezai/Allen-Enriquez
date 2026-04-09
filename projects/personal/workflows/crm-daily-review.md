# Workflow: Personal Brand CRM Daily Rhythm

## Schedule

| Time (PH) | What | How |
|---|---|---|
| ~6-7 PM | Evening briefing | `python3 tools/personal_crm.py evening-brief` |
| ~12:30 AM | Automated cleanup | Runs via launchd (moves rows to correct tabs) |

## Tab Structure

| Tab | Contents |
|---|---|
| Paint \| Call Queue | Uncalled + No Answer 1-4 (the calling tab) |
| Paint \| Warm Interest | Warm Interest + Meeting Booked |
| Paint \| Callbacks | Call Back + Late Follow Up + No Answer 5 |
| Paint \| Emails Sent | Leads with email sent |
| Paint \| Not Interested | Dead leads |
| Other \| * | Same structure for non-painting companies |

## Daily Flow
1. Evening brief promotes callbacks due today into Call Queue
2. Allen calls from Call Queue only
3. Cleanup moves leads out of Call Queue to correct tabs based on outcome

## Quick Commands
```
python3 tools/personal_crm.py review              # terminal stats
python3 tools/personal_crm.py cleanup --dry-run   # preview post-call moves
python3 tools/personal_crm.py evening-brief       # send briefing
python3 tools/personal_crm.py draft --row 3 --tab "Paint | Call Queue"
```

## Google Sheet
https://docs.google.com/spreadsheets/d/1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8
