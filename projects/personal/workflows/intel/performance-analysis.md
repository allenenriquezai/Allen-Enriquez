# Performance Analysis SOP

Track content and outreach performance. Identify what's working, what's dying, what to double down on.

## Schedule

| Frequency | Task |
|---|---|
| Daily | Update performance-scorecard.md (quick numbers) |
| Weekly | Deep analysis -- content + outreach what's-working docs |
| Monthly | Best Of breakdown + ads review |

## Data Sources

| Source | What it tells you |
|---|---|
| `projects/personal/.tmp/outreach_log.jsonl` | Outreach metrics -- contacts, response rates |
| `projects/personal/intel/competitor-moves.md` | What competitors are doing |
| `projects/personal/intel/icp-language.md` | What the audience wants |
| `projects/personal/intel/market-validation.md` | Pricing and PMF signals |
| Content metrics (when available) | Views, engagement, CTR per piece |

## What to Track

### Content Performance
Per piece: format, topic/hook, platform, views (day 1/7/30), engagement, CTR, leads generated.

**Rolling averages:** Last 10 pieces per format.

**Underperformance alert:** 3 consecutive pieces below rolling average = sound the alarm. Recommend a format/topic change.

### Outreach Performance
From outreach_log.jsonl: messages sent per day/week, response rate, positive response rate, conversion rate (response > call > client), best templates, best segments.

### Ads Performance (when running)
CPC, CPL, cost per call booked, ROAS, best creative/copy.

## Output Files

### `projects/personal/intel/performance-scorecard.md`

```markdown
# Performance Scorecard

> last_updated: YYYY-MM-DD

## This Week
| Metric | This week | Last week | Trend |
|---|---|---|---|
| Content published | X | X | up/down/flat |
| Total views | X | X | up/down/flat |
| Outreach sent | X | X | up/down/flat |
| Response rate | X% | X% | up/down/flat |
| Leads generated | X | X | up/down/flat |

## Rolling Averages (last 10 per format)
| Format | Avg views | Avg engagement | Avg leads |
|---|---|---|---|
| Short-form | X | X | X |
| Long-form | X | X | X |
| Post/thread | X | X | X |

## Alerts
- [Underperformance flags]
- [Formats to pause or change]
```

### `projects/personal/intel/content-whats-working.md`

Top performers, best hooks, best topics, what's NOT working, monthly Best Of breakdown.

### `projects/personal/intel/outreach-whats-working.md`

Best templates, best segments, best send times, what's NOT working.

### `projects/personal/intel/ads-whats-working.md`

Active campaigns, best creatives, best audiences, what to kill.

## Rules

- Never fabricate metrics. No data = "no data yet."
- Be blunt. "This is failing" not "this could be optimized."
- 3 below average = alarm. Don't soft-pedal it.
- Update docs. Don't overwrite. Keep history for trend visibility.
- Monthly Best Of must be detailed enough to replicate the success.

## Done

Print: top performer this period, biggest underperformance flag (if any), one thing to double down on, one thing to stop.
