# Ad Iteration Loop — Pillar 5 Self-Evidence Architecture

**Goal:** Daily Claude-driven creative iteration cycle that reads metrics, generates variants, pushes new ads, and kills underperformers. Allen's ₱5K/mo PH Meta campaign doubles as self-evidencing the Pillar 5 offer.

---

## How It Works (Pipeline)

```
Daily trigger (2am cron)
      ↓
[Meta API] Read yesterday metrics
      ↓
[Claude API] Generate 3 new variants from top performer + hook bank
      ↓
[Meta API] Push new creatives + ads to same campaign/adset
      ↓
[Meta API] Pause worst-performer if CPL >₱400 for 3 days
      ↓
[Database] Log iteration: ad_id, generated_at, source_hook, won_round, notes
      ↓
[Cron sleeps]
      ↓
Tomorrow, repeat.
```

---

## Key Numbers (Kill Criteria)

| Metric | Threshold | Action |
|---|---|---|
| **CPL (cost per lead)** | >₱400 sustained 3 days | Pause that ad |
| **Spend before 0 results** | >₱2,000 | Pause campaign, manual review required |
| **Form-fills with 0 calls booked** | >10 in 7 days | Flag ad-DM bridge issue (don't auto-pause; investigate) |
| **Daily new ads generated** | 3 | One from each of top-performer hook + alt-hook variant A + alt-hook variant B |

**CPL formula:** `total_spend / form_fills` (Meta provides this via `cost_per_action_type` with action="lead_form" or "offsite_conversion")

---

## Module Map

All modules live in `tools/personal/`:

| Module | Purpose | Location |
|---|---|---|
| **ad_iterator.py** | CLI + cron entry point | `tools/personal/ad_iterator.py` |
| **ad_config** | Per-ICP creative rules | `tools/enriquez2.0/outreach/ad-config.coaches.allen-self.md` (new file) |
| **Hook bank** | Copy variants from | `tools/enriquez2.0/content/icp-hooks.coaches.md` (Pillar 5 section) |
| **Landing page** | Form-fill destination | `projects/personal/sales/ad-landing-coaches/` |
| **Database** | Iteration state + metrics | `projects/personal/data/outreach.db` (extend with `ad_iterations` table) |
| **Graph API wrapper** | Raw Meta requests | Inline in `ad_iterator.py` using `requests` library |

---

## Daily Loop Logic (Detailed)

### Phase 1: Fetch Yesterday Metrics (6:00–6:05 AM)

```python
# Read last-24h metrics for all ACTIVE ads in the campaign
GET /v19.0/{AD_ACCOUNT_ID}/insights
  ?fields=
    ad_id,
    campaign_id,
    adset_id,
    campaign_name,
    spend,
    impressions,
    clicks,
    cost_per_action_type,  # extract action="lead_form" CPL
    actions,  # extract action="lead_form" count = form_fills
  &date_preset=yesterday
  &access_token={META_ADS_TOKEN}
```

**Stored:** DataFrame with columns: `ad_id | spend | impressions | clicks | cpl | form_fills | status`

**Filter:** Include only ads with status=ACTIVE. (Paused/archived ads skipped.)

**Early exit:** If any ad has spent >₱2K with 0 form-fills → pause entire campaign, log alert, return (manual review needed).

### Phase 2: Rank & Identify Top Performer (6:05–6:10 AM)

```python
# Sort by CPL (lowest = best)
# Tiebreaker: form_fills (higher = better)
top_performer = sorted(
  active_ads,
  key=lambda a: (a['cpl'], -a['form_fills'])
)[0]

# Store for variant generation
top_hook_id = top_performer['creative_hook_id']  # from db
```

**Database lookup:** Query `ad_iterations` table for the hook used in the top performer (joined on `ad_id`). If new ad, extract hook from Meta creative metadata or fall back to a default variant.

### Phase 3: Generate 3 Variants (6:10–6:20 AM)

Using Claude API (Haiku sufficient for fast iteration):

```python
prompt = f"""
You are generating ad copy variants for a coach audience (PH-domestic).

Source material:
- Hook bank: {hook_bank_pillar5_text}
- Top performer hook: {top_hook_id}
- Positioning: {coaches_positioning_excerpt}
- Voice rules: 3rd-grade reading, <10 words/sentence, no jargon, warm-direct

Generate 3 NEW ad copy variants (not the top performer repeated):
1. Variant A: Use an alternate hook from the bank, same pillar
2. Variant B: Swap the hook angle (e.g., if top is "time-back" frame, do "results-proof" frame)
3. Variant C: Pull from a completely different pillar (diversify if Pillar 5 saturation)

Each variant:
- Headline (max 30 chars)
- Primary text (max 125 chars)
- CTA button text (max 30 chars)

Output as JSON:
{{
  "variant_a": {{"headline": "", "text": "", "cta": "", "hook_used": ""}},
  "variant_b": {{"headline": "", "text": "", "cta": "", "hook_used": ""}},
  "variant_c": {{"headline": "", "text": "", "cta": "", "hook_used": ""}}
}}
"""

response = claude_api.messages.create(
  model="claude-3-5-haiku-20241022",
  max_tokens=500,
  messages=[{"role": "user", "content": prompt}]
)

variants = json.loads(response.content[0].text)
```

**Guard:** All variants must pass voice-rule validation (no jargon, <10 words/sentence). If Claude breaks rules, retry with stricter prompt.

### Phase 4: Push Variants to Meta (6:20–6:30 AM)

For each variant, create an ad creative + ad in the same campaign/adset:

```python
for variant_name, variant_data in variants.items():
  # Create adcreative
  creative_response = POST /v19.0/{AD_ACCOUNT_ID}/adcreatives
    {
      "name": f"coach-pillar5-{variant_name}-{date_now}",
      "object_story_spec": {
        "page_id": {META_PAGE_ID},
        "link_data": {
          "message": variant_data['text'],
          "headline": variant_data['headline'],
          "call_to_action": {
            "type": "LEARN_MORE",  # or "SUBSCRIBE"
            "value": {"link": "{landing_page_url}"}
          },
          "image_hash": "{existing_image_hash}"  # reuse creative asset
        }
      }
    }

  creative_id = creative_response['id']

  # Create ad (same adset as top performer)
  ad_response = POST /v19.0/{AD_ACCOUNT_ID}/ads
    {
      "name": f"coach-pillar5-{variant_name}-{date_now}",
      "adset_id": {top_performer_adset_id},
      "creative": {"creative_id": creative_id},
      "status": "ACTIVE",
      "daily_budget": 250 * 100  # ₱250/day = ₱7.5K/mo ÷ 30 days
    }

  # Log to db
  db.insert('ad_iterations', {
    'ad_id': ad_response['id'],
    'adset_id': top_performer_adset_id,
    'campaign_id': campaign_id,
    'generated_at': now(),
    'source_hook_id': variant_data['hook_used'],
    'variant_name': variant_name,
    'won_round': False,  # will flip to True if top performer tomorrow
    'notes': f"Generated from {top_hook_id}"
  })
```

**Daily budget allocation:** Total ₱5K/mo ÷ 30 days = ₱166.67/day. Distribute across 3-5 active ads. If 3 ads: ~₱55 each. If you want to give more to proven performers, allocate ₱100 to top performer + ₱33 to new variants.

### Phase 5: Pause Underperformers (6:30–6:35 AM)

```python
# Check for CPL degradation
for ad in active_ads:
  historical = db.query('ad_iterations').filter(
    ad_id=ad['id'],
    generated_at >= (now() - timedelta(days=3))
  )

  # If CPL >₱400 for all 3 of last 3 days
  if all(h['cpl'] > 400 for h in historical[-3:]):
    POST /v19.0/{ad['id']}
      {"status": "PAUSED"}

    db.update('ad_iterations', {'ad_id': ad['id']}, {
      'paused_at': now(),
      'pause_reason': 'sustained_high_cpl'
    })
```

**Do NOT auto-pause on day 1 of high CPL.** Meta has sampling noise. Need 3 days of sustained bad performance before action.

---

## Kill Criteria (Manual Gates)

| Condition | Action | Owner |
|---|---|---|
| Spend >₱2K, 0 form-fills | Pause campaign entirely, DM Allen alert | Loop (auto-pause campaign) |
| 10+ form-fills, 0 calls booked in 7 days | Flag in log + email Allen | Loop (email, not auto-pause) |
| CPL >₱400 for 3 consecutive days | Pause that ad | Loop (auto-pause ad) |
| No new metrics available (ad too new) | Carry forward yesterday's CPL, don't pause before day 2 | Loop (skip pause check) |

---

## Hook Bank Reference

All variants must pull from `tools/enriquez2.0/content/icp-hooks.coaches.md`, **Pillar 5 section only:**

- "I run my own paid ads with Claude API. 24-hour creative cycles. Here's the loop."
- "Most agencies iterate ad creative weekly. I do it daily. Here's the AI stack."
- "Your CPL is high because your creative is stale. Here's how to never be stale again."

**Voice rules** (from `positioning.md`):
- 3rd-grade reading level (Flesch-Kincaid grade ≤3)
- Sentences <10 words
- No jargon: "pillar," "system," "backend," "workflow," "agentic" — all forbidden in ad copy
- Warm, direct: "I did X, here's what happened" not "you should do X"

---

## State Persistence: `ad_iterations` Table

Extend `projects/personal/data/outreach.db` with:

```sql
CREATE TABLE ad_iterations (
  id INTEGER PRIMARY KEY,
  ad_id TEXT UNIQUE,
  adset_id TEXT,
  campaign_id TEXT,
  generated_at TIMESTAMP,
  source_hook_id TEXT,  -- which hook generated this ad
  variant_name TEXT,  -- "variant_a" | "variant_b" | "variant_c"
  won_round BOOLEAN DEFAULT 0,  -- set to 1 if this ad is top performer next day
  paused_at TIMESTAMP,
  pause_reason TEXT,  -- "sustained_high_cpl" | "campaign_pause" | etc
  notes TEXT
);
```

**Queries:**
- `SELECT * FROM ad_iterations WHERE won_round=1` → shows winning creatives over time
- `SELECT source_hook_id, COUNT(*) as wins FROM ad_iterations WHERE won_round=1 GROUP BY source_hook_id` → hook performance ranking

---

## Verification Commands (Test Before Deploying)

Run these one-liners to smoke-test each phase:

```bash
# 1. Can we read credentials?
export META_ADS_TOKEN="$(grep META_ADS_TOKEN /Users/allenenriquez/projects/personal/.env | cut -d= -f2)"
export META_AD_ACCOUNT_ID="$(grep META_AD_ACCOUNT_ID /Users/allenenriquez/projects/personal/.env | cut -d= -f2)"
echo "Token length: ${#META_ADS_TOKEN}, Account: $META_AD_ACCOUNT_ID"

# 2. Can we fetch metrics?
curl -s "https://graph.facebook.com/v19.0/${META_AD_ACCOUNT_ID}/insights?fields=spend,impressions,ad_id&date_preset=yesterday&access_token=${META_ADS_TOKEN}" | python3 -m json.tool | head -30

# 3. Can we connect to db?
sqlite3 /Users/allenenriquez/projects/personal/data/outreach.db ".tables"

# 4. Can we call Claude API?
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $(grep ANTHROPIC_API_KEY /Users/allenenriquez/projects/personal/.env | cut -d= -f2)" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-haiku-20241022","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' | jq '.content[0].text'
```

**All four should return data without errors.** If any fails, fix before running the loop.

---

## Deployment

1. **Create `tools/personal/ad_iterator.py`** — Main script with logic above + argparse for `--dry-run` testing.
2. **Create launchd plist** (`automation/com.enriquezOS.ad-iterator.plist`) → Daily 2:00 AM cron trigger.
3. **Test:** Run `python3 /Users/allenenriquez/tools/personal/ad_iterator.py --dry-run` to verify all phases without pushing to Meta.
4. **Deploy:** `launchctl load /Users/allenenriquez/automation/com.enriquezOS.ad-iterator.plist`
5. **Monitor:** Check `ad_iterations` table daily and watch CPL trend.

---

## Troubleshooting

| Issue | Debug step |
|---|---|
| Loop runs but no new ads appear | Check Meta account for pending approval (new creatives may be in review). Check launchd logs: `log show --predicate 'process=="launchd"' --last 1h \| grep ad-iterator` |
| Claude API errors (rate limit) | Loop already backs off 10s on 429. If persistent, reduce daily variants from 3 to 2. |
| CPL shooting up (all ads bad) | Landing page or form may have issues. Check form completion rate. May need to pause and investigate. |
| Metrics available but all zeros | First 6 hours of an ad campaign show 0 metrics. Wait until 6h old before trusting CPL. |
| Database locked | Likely concurrent script runs. Check if launchd is running loop twice. Use `fuser` to verify: `fuser /Users/allenenriquez/projects/personal/data/outreach.db` |

---

## Next: Ad Config File

Create `tools/enriquez2.0/outreach/ad-config.coaches.allen-self.md` with:
- Audience targeting (age 25-60, PH, interests: coaching, Skool, automation)
- Landing page URL + form fields
- Creative assets (image hash, brand guidelines)
- Daily budget split logic
- Escalation contacts (who gets alerted if campaign stalls)

That file = human-readable config; the loop reads it at startup to initialize Meta campaigns.
