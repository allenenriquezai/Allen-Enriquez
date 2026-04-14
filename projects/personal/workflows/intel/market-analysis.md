# Market Analysis SOP

Validate Allen's offer and pricing against real market data. Track what similar services cost, objections, and product-market fit signals.

## Schedule

Biweekly (1st and 15th of each month). Triggerable on demand.

## What to Research

### 1. Competitor Pricing

| Source | Search Terms |
|---|---|
| Upwork | "AI automation specialist", "Claude developer", "n8n developer", "AI agent builder" |
| Fiverr | Same terms -- note package prices |
| Agency websites | AI automation agencies -- pricing pages |
| Courses | AI automation course pricing |
| Coaching | AI consultant hourly rates |

### 2. Offer Structures

Track how competitors structure offers: one-time build, monthly retainer, course, coaching, hybrid (free course + paid DFY), revenue share.

### 3. Objections & Friction

Search for: "AI automation not worth it", "AI automation scam", "why I cancelled my AI automation service", "AI automation agency review", negative comments on competitor content.

Track what makes people NOT buy.

### 4. PMF Signals (from Allen's data)

When data is available, check:
- `projects/personal/.tmp/outreach_log.jsonl` -- response rates
- CRM data -- conversion rates
- Content metrics -- which topics get engagement
- DM conversations -- what resonates

## Output

Write to `projects/personal/reference/intel/market-validation.md`:

```markdown
# Market Validation

> last_updated: YYYY-MM-DD

## Pricing Landscape

### Done-For-You AI Automation
| Source | Low | Mid | High |
|---|---|---|---|
| Upwork (hourly) | $X | $X | $X |
| Upwork (project) | $X | $X | $X |
| Fiverr | $X | $X | $X |
| Agencies | $X | $X | $X |

### Courses / Coaching
| Type | Price range |
|---|---|
| Courses | $X-$X |
| Hourly consulting | $X-$X |
| Monthly retainer | $X-$X |

## Allen's Position
- [Recommendation with reasoning]
- [Comparison to market]

## Objections Found
| Objection | How common | How to handle |
|---|---|---|
| "[Objection]" | [Frequent/rare] | [Response strategy] |

## PMF Signals

### Positive (we have fit)
- [Signal] -- [evidence]

### Negative (we don't have fit yet)
- [Signal] -- [evidence]

### Unknown (need more data)
- [What we need to test]

## Recommended Next Steps
1. [Action] -- [why]

## Archive
### [Previous date]
[Old data moved here]
```

## Rules

- Real prices only. Never guess. If not public, write "not public."
- Convert all prices to USD AND PHP.
- PMF Signals is the most important section. Be brutally honest.
- If Allen doesn't have PMF yet, say so clearly and say what's missing.
- Objections are gold. More = better content and sales handling.
- Update the doc. Don't overwrite. Archive old data.

## Done

Print: recommended price point (with range), top 3 objections to address in content, PMF verdict (yes/no/not enough data).
