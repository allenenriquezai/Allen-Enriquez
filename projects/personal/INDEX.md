# Personal Workspace — Storage Index

Map of where everything Allen saves lives. Claude reads on demand; not auto-loaded into context.

**Rule of thumb:**
- Text under 1MB → local markdown/JSON/JSONL
- Binary / media (PDF, image, video, audio) → Google Drive (linked from `files/INDEX.md`)

## Folders

| Folder | What | Format | Filename convention |
|---|---|---|---|
| `goals/` | Current 30-day + weekly priorities | markdown | `current.md` (single live file) |
| `journal/` | Daily EOD reflections | markdown | `YYYY-MM-DD.md` |
| `library/notes/` | General notes | markdown | `{slug}.md` |
| `library/projects/` | Project-scoped docs | markdown | `{slug}.md` |
| `library/links/` | Bookmarks with tags | markdown | `links.md` (single file, list) |
| `files/` | **Catalog only** — actual binaries in Google Drive | markdown | `INDEX.md` (rows: filename, Drive URL, Drive ID, tags, caption, uploaded) |
| `content/calendar.json` | Planned + posted content by date/platform | JSON | single file |
| `content/scripts/` | Content scripts (idea → script → filmed → posted) | markdown w/ frontmatter | `{slug}.md` (frontmatter: `status`, `platform`, `hook`, `created`) |
| `content/ideas.md` | Quick idea capture | markdown | single file |
| `campaigns/{name}/` | Per-campaign offer + icp + assets + pipeline | markdown + JSON | `offer.md`, `icp.md`, `assets.md`, `pipeline.md`, `sources.json` |
| `outreach/prospects.jsonl` | Unified multi-channel prospect records | JSONL | one line per prospect |
| `outreach/log.jsonl` | Send + reply events | JSONL | append-only |
| `outreach/templates/` | Per-channel message templates | markdown | `{channel}_{type}_t{n}.md` |
| `reference/` | Intel, style guides, configs (hand-maintained) | markdown + YAML | various |
| `ideas/` | Free-form idea docs (future features, bets) | markdown | `{slug}.md` |

## How Claude uses this

- "What's my current goal?" → read `goals/current.md`
- "How have I felt this week?" → read last 7 files in `journal/`
- "What scripts are ready to film?" → grep `content/scripts/` for `status: script-ready`
- "Who's waiting on a reply?" → tail `outreach/log.jsonl` where `status=Replied`
- "What files have I uploaded?" → read `files/INDEX.md`
- "Where do X live?" → this file

Never auto-pushed. Always on demand.

## Schema: `content/scripts/{slug}.md`

```
---
status: idea | script-ready | filmed | posted
platform: instagram | facebook | tiktok | youtube | all
hook: "one-line hook"
created: 2026-04-18
posted: 2026-04-20  # optional, when status=posted
---

# Title

Body of script...
```

## Schema: `outreach/prospects.jsonl`

```json
{"id": "...", "name": "...", "channel": "fb_group|fb_dm|ig_dm|tiktok_dm|email", "source": "...", "stage": "discover|enrich|messaged|replied|booked|closed", "campaign": "us-painters|ph-outbound", "last_contact": "2026-04-18", "notes": "..."}
```

## Schema: `outreach/log.jsonl`

```json
{"ts": "2026-04-18T09:15:00+08:00", "prospect_id": "...", "channel": "fb_dm", "action": "sent|replied|booked|closed", "template": "recruitment_fb_t1", "content": "..."}
```

## Schema: `files/INDEX.md` rows

Markdown table. App appends one row per upload:

```
| filename | drive_url | drive_id | tags | caption | uploaded |
|---|---|---|---|---|---|
| pitch-deck-v3.pdf | https://drive.google.com/... | 1AbCd... | pitch,sales | For US painter cold call | 2026-04-18 |
```

## Updating this file

When the app adds a new folder or schema, it appends a row here. Hand-edit for conventions. Keep under 150 lines — the point is Allen (or Claude) scans this in 30 seconds.
