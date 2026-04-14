# Re-engagement Workflow

Re-engage previous clients for repeat business, Google reviews, and referrals. Win back lost deals.

---

## When to Run

- **Clients:** Weekly, Monday AM (automated via `reengage_campaign.py`)
- **Lost deals:** Weekly, same run
- **Manual:** On demand when Allen requests

## Tool

```bash
python3 tools/reengage_campaign.py --mode all          # scan both
python3 tools/reengage_campaign.py --mode clients       # repeat business only
python3 tools/reengage_campaign.py --mode lost          # win-back only
python3 tools/reengage_campaign.py --dry-run            # preview
python3 tools/reengage_campaign.py --send               # send approved emails
```

## Pipeline

### Previous Clients (--mode clients)

```
Completed Project → Re-engagement Board (New / For Review) → Scan → Draft Email → Allen Approves → Send → Track Response
```

**Sources:**
- Pipedrive Projects Board 3 (EPS Clean Re-engagement): phase "New / For Review"
- Pipedrive Projects Board 5 (EPS Paint Re-engagement): phase "New / For Review"

**Outreach sequence:**
1. Check-in email — "How's everything? Any upcoming work?"
2. If response positive → create new deal
3. Google review ask — "Would you leave us a review?"
4. If no response after 2 weeks → move to "Not Interested"

### Lost Deals (--mode lost)

```
Lost Deal (last 6 months) → Filter → Draft Win-back Email → Allen Approves → Send → Track Response
```

**Filters (auto-skip):**
- Loss reason: "project cancelled"
- Loss reason: "not going ahead"
- Loss reason: "duplicate"

**Outreach:**
- Single email — "Has anything changed? Happy to re-quote."
- If response positive → reopen deal or create new one
- If no response → leave as lost

## Review Process

1. Tool outputs candidates to `.tmp/reengage_clients.json` and `.tmp/reengage_lost.json`
2. Morning briefing surfaces count: "5 clients ready for re-engagement"
3. Allen reviews candidates and draft emails
4. Mark approved candidates (set `"approved": true` in JSON)
5. Run `--send` to send approved emails

## Pipedrive Project Phases

### Re-engagement Boards (3 + 5)
| Phase | Meaning |
|---|---|
| New / For Review | Ready for outreach |
| Added to Sequence | Email sent, waiting for response |
| Contact Made / Responded | Client replied |
| Google Review Done | Review received |
| Interested / Cross-sell | Repeat business opportunity |
| Not Interested | No response or declined |

## Rules

- Never send without Allen's approval
- One email per client per month max
- Skip clients already in active deals
- Track all responses — move project phase accordingly
- If "Interested / Cross-sell" → create new deal in main pipeline
