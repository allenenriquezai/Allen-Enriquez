# Content Hub Architecture

App architecture: tables, API routes, R2 layout, integrations, env vars. Read at session start when working in `tools/content-hub/`.

## What it does

Multi-platform content production system. Captures inspiration (creator feed, learning refs, inbox), generates ideas + reel/carousel/long-form scripts via Claude, uploads media assets to Cloudflare R2, schedules posts on a calendar, publishes to Instagram / Facebook / YouTube / TikTok with platform-specific captions, and ingests analytics back. Inbox surfaces comments + DMs from every platform for reply.

## Top-level UI (after April 2026 refactor)

| Tab | Path | What |
|---|---|---|
| Projects | `/projects` | **Kanban (main view)** — every project, columns auto-derive from `v_project_status` |
| Calendar | `/calendar` | Month grid, drag-drop slot edit, status colors |
| Studio (Scripts) | `/scripts` | Script list view with project context |
| Studio (Notes) | `/ideation` | Free-form notes scratchpad — promote to project |
| Inspiration | `/inspiration` | Creator feed, viral refs, trending, competitors. "Create project" button on every row. |
| Library | `/library` | Asset grid (short-form / long-form / carousels). Project link + status badge per tile. |
| Library detail | `/library/[id]` | Multi-platform caption editor + post bar |
| Inbox | `/inbox` | Comments + DMs from all platforms |
| Analytics | `/analytics` | Per-platform charts (recharts) |
| Docs | `/docs` | This documentation |

## Data model

### Projects = `ideas` table (UI-renamed)

The `ideas` table is the project root. UI calls it "project". Same table, broader semantics.

```
projects (ideas) ──┬── scripts (idea_id)
                   │     ├── variant=reel       → "short-form" script
                   │     ├── variant=youtube    → "long-form" script
                   │     ├── variant=carousel   → carousel script
                   │     └── variant=caption_*  → per-platform captions
                   │
                   └── assets (idea_id, script_id, status, local_path)
                         └── posts (asset_id, platform_post_id)
                               └── metrics (post_id)

schedule (script_id, asset_id) — calendar slots
ideation_notes (idea_id nullable) — free-form notes, optional project link
```

### Computed status

```sql
CREATE VIEW v_project_status AS
SELECT i.id AS project_id,
       CASE
         WHEN i.archived=1 THEN 'archived'
         WHEN EXISTS(... posts joined to project assets) THEN 'posted'
         WHEN EXISTS(... schedule rows for project assets) THEN 'scheduled'
         WHEN EXISTS(... assets WHERE status='ready') THEN 'ready'
         WHEN EXISTS(... assets WHERE status='animating') THEN 'animating'
         WHEN EXISTS(... assets WHERE status='editing') THEN 'editing'
         WHEN EXISTS(... scripts) THEN 'scripted'
         ELSE 'draft'
       END AS status
FROM ideas i;
```

### Schema

`lib/schema.sql` — 18 tables. Migrations idempotent on every `npm start` via `init-railway.ts`. Key project lifecycle additions (April 2026):

| Table | Column | Purpose |
|---|---|---|
| `ideas` | `archived` | Project archived flag (drag-to-archive in Kanban) |
| `ideas` | `source_type` | `raw \| competitor_post \| viral_ref \| trending` |
| `ideas` | `source_ref_table`, `source_ref_id` | FK back to inspiration row |
| `assets` | `status` | `editing \| animating \| ready \| posted \| archived` |
| `assets` | `script_id` | FK to scripts row that this asset implements |
| `assets` | `local_path` | Filesystem path on creator's mac at render time |
| `assets` | `render_meta_json` | Skill metadata: composition_id, scene_count, audio_duration |
| `posts` | `platform_post_id` | IG media_id, YT video_id, TikTok video_id, FB post_id |
| `posts` | `platform_meta_json` | Raw API response for debugging |
| `ideation_notes` | `idea_id` | Pin a note to a project |

## R2 layout (canonical)

```
r2://content-hub/
  ready/<project_id>/<asset_id>-<slug>.mp4    # rendered, awaiting post
  posted/<yyyy-mm>/<asset_id>-<slug>.mp4      # renamed on first successful post
  archived/<asset_id>-<slug>.mp4              # cold (TODO)
  source/<project_id>/capcut-export.mov       # optional CapCut backup
  thumbnails/<asset_id>.jpg
  uploads/<ts>-<filename>                     # legacy direct uploads (still served)
```

R2 is canonical. Local `video-projects/<slug>/` is scratchpad only — moment a render lands in `ready/`, the canonical copy is R2.

**Cost math** at Allen's volume (3 short-form/day + 2-3 long-form/week ≈ 9 GB/mo new): ~$1.62/mo storage at year 1. Egress free.

## Key API groups (`app/api/*/route.ts`)

| Group | Endpoints |
|---|---|
| **Projects (NEW)** | `projects` (list with computed status), `projects/[id]/state` (phase ping), `projects/from-source`, `projects/from-note` |
| **Library** | `library`, `library/[id]`, `library/sync`, `library/promote` (NEW — auto-link from skills), `library/[id]/syndicate-captions` |
| **Upload** | `upload/presigned` |
| **Ideation** | `ideas/generate`, `ideas/rewrite`, `ideas/carousel`, `ideas/backfill-scripts`, `ideas/import-link`, `ideation`, `ideation/tags`, `ideation/reseed` |
| **Week planning** | `week-plan/suggest`, `week-plan/save`, `week-plan/generate` |
| **Scripts** | `scripts`, `scripts/list`, `scripts/[id]` |
| **Schedule** | `schedule`, `schedule/[id]` |
| **Publish per platform** | `{facebook,instagram,youtube,tiktok}/publish` (returns platform_post_id), `/edit`, `/comments`, `/comments/reply`, `/conversations`, `/conversations/reply` |
| **Posts** | `posts` (logs every publish attempt; on success: marks asset.status='posted' + moves R2 key) |
| **Auth per platform** | `youtube/auth`, `youtube/auth/callback`, `tiktok/auth`, `tiktok/auth/callback`, `instagram/refresh-token`, `instagram/token-status` |
| **Analytics** | `analytics/{youtube,instagram,facebook,tiktok}`, `analytics/youtube/{traffic-sources,retention}` |
| **Inbox** | `inbox`, `inbox/[id]` |
| **Creator feed** | `creator-feed`, `creator-feed/refresh`, `creator-feed/last-refresh` |
| **Metrics** | `metrics` |
| **Docs (NEW)** | `/docs/[[...slug]]` |

## Background scripts (`scripts/*.ts`)

| Script | Trigger | What |
|---|---|---|
| `init-railway.ts` | `npm start` | Apply schema.sql, run idempotent ALTER TABLE migrations, create `v_project_status` view |
| `verify-integrity.ts` | manual / cron | Flag orphan assets (NULL project_id/script_id) |
| `migrate.ts` | `npm run migrate` | Ad-hoc migration template |
| `seed.ts`, `seed-{ideation,learning,calendar}.ts` | `npm run seed` | Sample data |
| `set-r2-cors.ts` | manual | Configure R2 bucket CORS via S3 API |

## Skills that touch Content Hub

| Skill | What it writes |
|---|---|
| `/short-form-video` | After final render → `POST /api/library/promote` → uploads MP4 + INSERT assets row |
| `/scene-animation` | Optional `POST /api/projects/:id/state {phase: 'animating'}` |
| `/carousel` | Reads transcript.json, posts carousel slides |
| `/content-research` | Writes to `learning_refs`, `creator_posts` |
| `/content` | Writes to `schedule`, queries `ideas` |

## Env vars (`.env.local` local + Railway prod)

- **Anthropic:** `ANTHROPIC_API_KEY`
- **R2:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`
- **Meta (FB + IG):** `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `INSTAGRAM_ACCOUNT_ID`, `INSTAGRAM_USER_TOKEN`
- **YouTube:** `YOUTUBE_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`
- **TikTok:** `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- **DB:** `DATABASE_PATH` (Railway: `/data/content_hub.db`, local: `./content_hub.db`)
- **Optional:** `BLOTATO_API_KEY`, `IS_RAILWAY`, `CREATOR_FEED_AUTO_REFRESH`

## Failure modes

| Issue | Where | Mitigation |
|---|---|---|
| IG Reels rejects R2 pub URLs (error 2207076) | `app/api/instagram/publish` | Resumable byte upload via `rupload.facebook.com` (FIXED) |
| Module-level DB queries crash Railway build | route modules | `CREATE TABLE IF NOT EXISTS` + `export const dynamic = 'force-dynamic'` on DB-touching routes |
| IG user token expires ~60 days, no auto-refresh cron | `oauth_tokens` table | Manual refresh via `/api/instagram/token-status`. Inbox surfaces failure. |
| TikTok analytics ingested but no chart | `/analytics` page | Data in `tiktok_stats`, UI deferred |
| `creator-feed/refresh` crashes Railway | `app/api/creator-feed/refresh` | Guarded by `IS_RAILWAY` env var → 503 if true |
| Duplicate R2 objects from drafts/ready/uploads paths | library sync | Hide/delete UI = v1 fix; content-hash dedupe deferred |
| FB + TikTok apps under platform review | external | Routes written, end-to-end untested until approved |
| Missing env var on Railway vs `.env.local` | startup | Cross-check `railway variables --kv` vs `.env.local` before deploy |
| Orphan assets with NULL project_id | post-render auto-promote skipped | Library "Unlinked" filter surfaces them; manual project picker per tile |

## Dependencies

- **External:** Anthropic, Cloudflare R2, Meta Graph (FB+IG), YouTube Data v3, TikTok API, Railway (deploy + `/data` volume)
- **Internal:** standalone — does NOT import from `tools/shared/` or `tools/enriquez2.0/`
- **Stack:** Next.js 16.2.4, React 19.2.4, TypeScript 5, better-sqlite3, AWS SDK S3 client (R2), Anthropic SDK, recharts, dnd-kit, react-markdown, Tailwind 4

## Production

- **Deployed:** `https://content-hub-production-b28e.up.railway.app`
- **Branch:** `main` — Railway deploys from GitHub on push
- **DB persistence:** Railway `/data` volume

## Last verified

2026-04-25 — kanban refactor + project lifecycle (`/projects`, `v_project_status`, `library/promote`, `posts.platform_post_id`)
