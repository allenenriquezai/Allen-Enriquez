# PH Outreach System

Automated outbound pipeline for PH market. Discovers prospects, enriches them, generates personalised messages, tracks follow-ups. You review + send manually. Target: 5 emails + 10 FB DMs per day, ~15 min of your time.

**Segments:** Recruitment + VA agencies, Real estate brokerages.

## What's built

| File | Purpose |
|---|---|
| `tools/personal/outreach.py` | Main CLI |
| `tools/personal/outreach_sources.py` | Discovery (Places, BusinessList, JobStreet, Kalibrr, FB inbox) |
| `tools/personal/outreach_enrich.py` | Website scrape, email finder, FB Graph, Haiku hook |
| `tools/personal/outreach_messages.py` | 12 templates + Haiku message generator |
| `tools/personal/outreach_lifecycle.py` | log-sent, follow-ups, reply drafting |
| `projects/personal/outreach/templates/*.md` | 12 message templates |
| `projects/personal/reference/outreach_config.yaml` | Limits, segments, pain points |
| `projects/personal/.tmp/fb_prospects_inbox.txt` | Where you drop FB URLs |
| Sheet: [PH Outreach](https://docs.google.com/spreadsheets/d/15NvyLkAWya3ZNxT-R1dSPTVN1z2CyKEzDTdfxHY38Do/edit) | Prospect CRM |

## One-time setup (~30 min)

### 1. Enable Google Places API

- Open the existing GCP project that hosts your Gmail/Sheets OAuth
- Enable "Places API (New)"
- Create an API key, restrict to Places API
- Add to `projects/personal/.env`:
  ```
  GOOGLE_PLACES_API_KEY=...
  ```

Free tier: $200/mo credit = ~5K-10K PH businesses discovered per month.

### 2. Snov.io free account (optional but recommended)

- Sign up https://app.snov.io (50 credits/mo free)
- Get Client ID + Secret from API settings
- Add to `.env`:
  ```
  SNOV_CLIENT_ID=...
  SNOV_CLIENT_SECRET=...
  ```

### 3. Hunter.io free fallback (optional)

- Sign up https://hunter.io (25 searches/mo free)
- Add to `.env`:
  ```
  HUNTER_API_KEY=...
  ```

### 4. FB Graph token (optional, for public page data)

- https://developers.facebook.com/apps -> create app -> "Business"
- Get page access token (read_only, no user scope)
- Add to `.env`:
  ```
  FB_GRAPH_TOKEN=...
  ```

Skip any of these and that enrichment path just returns empty — pipeline still works.

### 5. Load launchd jobs

```bash
launchctl load /Users/allenenriquez/Desktop/Allen\ Enriquez/automation/com.enriquezOS.ph-outreach-daily.plist
launchctl load /Users/allenenriquez/Desktop/Allen\ Enriquez/automation/com.enriquezOS.ph-outreach-discover.plist
```

- **Daily 6am:** enrich new rows -> generate queue -> check follow-ups -> poll email replies -> WhatsApp you when done
- **Sunday 3am:** weekly discovery run across all sources

## Daily workflow (yours — 15 min)

1. **Morning:** WhatsApp notification says "PH outreach ready: 15 messages"
2. Open `projects/personal/.tmp/outreach_queue_YYYY-MM-DD.md`
3. Send emails from Gmail (copy subject + body)
4. Open each FB URL, paste DM, send
5. Run: `python3 tools/personal/outreach.py log-sent --ids 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15`

## Weekly workflow (yours — 20 min)

1. Join 1-2 new PH FB groups (recruitment/VA/real estate)
2. Browse groups, drop prospect URLs into `projects/personal/.tmp/fb_prospects_inbox.txt`
3. Sunday discovery run automatically pulls them + new Places/JobStreet results

## Manual CLI (for ad-hoc runs)

```bash
# Add prospects from all sources
python3 tools/personal/outreach.py discover --segment recruitment --limit 50

# Dry-run first
python3 tools/personal/outreach.py discover --segment recruitment --dry-run

# Enrich new rows (fills email, FB URL, Haiku personal hook)
python3 tools/personal/outreach.py enrich --limit 10

# Generate today's queue (5 emails + 10 DMs)
python3 tools/personal/outreach.py queue

# Mark sent after you finish
python3 tools/personal/outreach.py log-sent --ids 1,2,3

# See the funnel
python3 tools/personal/outreach.py stats

# Check for follow-ups manually
python3 tools/personal/outreach.py followups

# Poll Gmail replies + draft responses
python3 tools/personal/outreach.py replies
# Drafts land in projects/personal/.tmp/reply_drafts.md
```

## Guardrails (cannot be bypassed)

- **Send stays manual.** No auto-send ever.
- **Email warm-up:** week 1 = 3/day, week 2 = 5, week 3 = 8, week 4 = 10, then 15 cap.
- **FB DMs:** hard cap 12/day (under Facebook's 15/day ban threshold).
- **Opt-out keywords** auto-mark prospects `do_not_contact`. No re-contact.
- **FB group scraping:** off-limits (ban risk). You join groups manually.
- **No identical messages.** Haiku temp 0.7 + per-prospect personalisation.

## Cost

- $0/mo base (Gmail, Sheets, Places free credits, Snov/Hunter free tiers)
- ~$3-5/mo Anthropic Haiku for personalisation + reply drafting

## First-run sequence

```bash
# 1. Add a few FB prospects to the inbox manually
#    projects/personal/.tmp/fb_prospects_inbox.txt

# 2. Ingest them
python3 tools/personal/outreach.py discover --source fb_inbox

# 3. Enrich
python3 tools/personal/outreach.py enrich --limit 5

# 4. Check sheet — personal hooks should be filled
python3 tools/personal/outreach.py stats

# 5. Generate first queue
python3 tools/personal/outreach.py queue

# 6. Review projects/personal/.tmp/outreach_queue_YYYY-MM-DD.md
#    Send a couple. Run log-sent.

# 7. After 3 days, run followups — Touch 2 appears in queue automatically
```
