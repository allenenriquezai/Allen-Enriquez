# Executive Assistant

Cross-project AI assistant that monitors and acts across EPS and personal accounts.

## Scope
1. **EPS** — Pipedrive CRM, sales@epsolution.com.au Gmail
2. **Personal** — allenenriquez@gmail.com Gmail, Google Calendar (both accounts)

## Tools
- `tools/crm_monitor.py` — Pipedrive pipeline scan → action items (JSON)
- `tools/morning_briefing.py` — two-bucket triage briefing (Allen's Plate vs AI Can Handle)
- `tools/briefing_action_loop.py` — processes Allen's reply to briefing, executes approved AI actions
- `tools/ai_learning_brief.py` — daily AI education email (mini-course topic + expert digest)

## Credentials
- EPS: `projects/eps/.env` (Pipedrive keys), `projects/eps/token_eps.pickle` (Gmail OAuth)
- Personal: `projects/personal/token_personal.pickle` (Gmail/Calendar/Send OAuth)

## Briefing v2 — Two-Bucket Triage

Sends from personal Gmail (`allenenriquez@gmail.com`) to `allenenriquez006@gmail.com`.

**Allen's Plate** (amber) — things only Allen can do:
- All CRM deals & activities
- Today's EPS calendar (calls, site visits, meetings)

**AI Can Handle** (blue) — numbered items Allen can approve:
- Customer inquiry emails → AI drafts response
- Follow-up chase emails → AI drafts via `draft_follow_up_email.py`
- Stale deals → AI sends check-in

**Action loop:** Reply to briefing with `GO 1,2,3` or `GO ALL` or `SKIP 4`. Action loop parses and executes.

## Schedule (launchd)

| Plist | Time | What |
|---|---|---|
| `com.enriquezOS.morning-briefing.plist` | 6:30 AM | Send morning briefing |
| `com.enriquezOS.ai-learning-brief.plist` | 7:00 AM | Send AI learning brief |
| `com.enriquezOS.briefing-action-loop.plist` | 7:30 AM | Process Allen's reply |

Install:
```
cp com.enriquezOS.morning-briefing.plist ~/Library/LaunchAgents/
cp com.enriquezOS.ai-learning-brief.plist ~/Library/LaunchAgents/
cp com.enriquezOS.briefing-action-loop.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.enriquezOS.morning-briefing.plist
launchctl load ~/Library/LaunchAgents/com.enriquezOS.ai-learning-brief.plist
launchctl load ~/Library/LaunchAgents/com.enriquezOS.briefing-action-loop.plist
```

## Status
- Phase 1: Done (data layer — CRM monitor + briefing)
- Phase 2: Done (triage layout + action loop + schedule)
- Phase 3: Not started (autonomous action — WhatsApp, auto-responses, JustCall text on new lead)

## Temp files
- `.tmp/morning_briefing.html` — latest briefing preview
- `.tmp/ai_learning_brief.html` — latest learning brief preview
- `.tmp/briefing_actions.json` — action manifest for the loop
- `.tmp/briefing-cron.log` — launchd output
- `.tmp/ai-learning-brief-cron.log` — learning brief launchd output
