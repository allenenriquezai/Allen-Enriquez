# content-hub — System Overview

## What it does

Multi-platform content production system. Captures inspiration (creator feed, learning refs, inbox), generates ideas + reel/carousel/long-form scripts via Claude, uploads media assets to Cloudflare R2, schedules posts on a calendar, publishes to Instagram / Facebook / YouTube / TikTok with platform-specific captions, and ingests analytics back. Inbox surfaces comments + DMs from every platform for reply.

## Data flow

```mermaid
flowchart LR
    subgraph Capture
        CR[creator-feed<br/>YouTube/TikTok poll]
        LR[learning_refs]
        INB[inbox<br/>comments + DMs]
    end
    subgraph Studio
        IDE[/ideation/<br/>notes + tags]
        WP[/scripts/<br/>week planner]
        IDEAS[ideas + scripts<br/>tables]
    end
    subgraph Assets
        R2[(Cloudflare R2)]
        ASSETS[assets table]
    end
    subgraph Publish
        SCH[/calendar/<br/>schedule slots]
        Q[/queue/<br/>quick publish]
        POSTS[posts + metrics]
    end
    subgraph Analytics
        AN[/analytics/<br/>charts]
    end

    CR --> IDEAS
    LR --> WP
    WP --> IDEAS
    IDE --> IDEAS
    IDEAS --> SCH
    BROWSER[browser XHR upload] --> R2
    R2 --> ASSETS
    ASSETS --> SCH
    SCH --> Q
    Q -->|publish/schedule| FB[Facebook Graph]
    Q -->|publish/schedule| IG[IG Graph<br/>resumable upload]
    Q -->|publish/schedule| YT[YouTube Data v3<br/>OAuth]
    Q -->|publish/schedule| TT[TikTok API<br/>PKCE]
    FB & IG & YT & TT --> POSTS
    FB & IG & YT & TT --> AN
    FB & IG & YT --> INB
```

## Entry points

### App routes (`app/*/page.tsx`)
| Route | What |
|---|---|
| `/calendar` | Month grid, drag-drop slot edit, status colors |
| `/queue` | Assets awaiting publish, quick-publish modal |
| `/scripts` | Studio — Kanban + week planner (AI day-themes) |
| `/ideation` | Notes + tags, idea capture |
| `/learning` | Trending references |
| `/inspiration` | Curated creator posts |
| `/inbox` | Comments + DMs from all platforms |
| `/creator-feed` | Subscribed creator video feed |
| `/library` | Asset library (short-form / long-form / carousels) |
| `/library/[id]` | Asset detail — multi-platform caption editor + post bar |
| `/analytics` | Per-platform charts (recharts) |

### Key API groups (`app/api/*/route.ts`)
- **Upload + Library:** `upload/presigned`, `library`, `library/[id]`, `library/sync`
- **Ideation:** `ideas/generate`, `ideas/rewrite`, `ideas/carousel`, `ideas/backfill-scripts`, `ideas/import-link`, `ideation`, `ideation/tags`
- **Week planning:** `week-plan/suggest`, `week-plan/save`, `week-plan/generate`
- **Scripts:** `scripts`, `scripts/list`, `scripts/[id]`
- **Schedule:** `schedule` (year/month query), `schedule/[id]`
- **Publish per platform:** `{facebook,instagram,youtube,tiktok}/publish`, `/edit`, `/comments`, `/comments/reply`, `/conversations`, `/conversations/reply`
- **Auth per platform:** `youtube/auth`, `youtube/auth/callback`, `tiktok/auth`, `tiktok/auth/callback`, `instagram/refresh-token`, `instagram/token-status`
- **Analytics:** `analytics/{youtube,instagram,facebook,tiktok}`, `analytics/youtube/{traffic-sources,retention}`
- **Inbox:** `inbox` (filter), `inbox/[id]`
- **Creator feed:** `creator-feed`, `creator-feed/refresh`, `creator-feed/last-refresh`

### Background scripts (`scripts/*.ts`)
| Script | Trigger | What |
|---|---|---|
| `init-railway.ts` | `npm start` | Apply schema.sql, run idempotent migrations |
| `migrate.ts` | `npm run migrate` | Ad-hoc migration template |
| `seed.ts`, `seed-{ideation,learning,calendar}.ts` | `npm run seed` | Sample data |
| `set-r2-cors.ts` | manual | Configure R2 bucket CORS via S3 API |

## Inputs

### Env vars (`.env.local` local + Railway prod)
- **Anthropic:** `ANTHROPIC_API_KEY`
- **R2:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`
- **Meta (FB + IG):** `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `INSTAGRAM_ACCOUNT_ID`, `INSTAGRAM_USER_TOKEN`
- **YouTube:** `YOUTUBE_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`
- **TikTok:** `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- **DB:** `DATABASE_PATH` (Railway: `/data/content_hub.db`, local: `./content_hub.db`)
- **Optional:** `BLOTATO_API_KEY`, `IS_RAILWAY`, `CREATOR_FEED_AUTO_REFRESH`

### Schema
`lib/schema.sql` — 17 tables: `ideas`, `scripts`, `schedule`, `assets`, `posts`, `metrics`, `inbox`, `learning_refs`, `creator_posts`, `facebook_posts`, `instagram_posts`, `tiktok_stats`, `youtube_stats`, `oauth_tokens`, `ideation_notes`, `ideation_tags`, `week_themes`. Migrations run idempotently on every `npm start` via `init-railway.ts`.

## Outputs

- **DB writes:** all tables above. SQLite WAL mode (`lib/db.ts`).
- **R2:** `https://pub-329ed64a6ef54f5d921e351060c047c5.r2.dev/uploads/{ts}-{filename}` — public CDN.
- **External calls:**
  - FB Graph v25.0 → `/feed`, `/videos`, `/insights`
  - IG Graph v25.0 → `/media` (resumable via `rupload.facebook.com`), `/media_publish`, `/insights`
  - YT Data v3 → `/videos` (resumable), `/search`, analytics endpoints
  - TikTok → `/post/publish/action/upload`, `/video/list`
- **No file logs** — stdout/stderr only.

## Failure modes

| Issue | Where | Mitigation |
|---|---|---|
| IG Reels rejects R2 pub URLs (error 2207076) | `app/api/instagram/publish` | Resumable byte upload via `rupload.facebook.com` (FIXED) |
| Module-level DB queries crash Railway build | route modules | `CREATE TABLE IF NOT EXISTS` + `export const dynamic = 'force-dynamic'` on DB-touching routes |
| IG user token expires ~60 days, no auto-refresh cron | `oauth_tokens` table | Manual refresh via `/api/instagram/token-status`. Inbox surfaces failure. Cron deferred. |
| TikTok analytics ingested but no chart | `/analytics` page | Data in `tiktok_stats`, UI deferred |
| `creator-feed/refresh` crashes Railway | `app/api/creator-feed/refresh` | Guarded by `IS_RAILWAY` env var → 503 if true |
| Duplicate R2 objects from drafts/ready/uploads paths | library sync | Hide/delete UI = v1 fix; content-hash dedupe deferred Q2 |
| FB + TikTok apps under platform review | external | Routes written, end-to-end untested until approved |
| Missing env var on Railway vs `.env.local` | startup | Cross-check `railway variables --kv` vs `.env.local` before deploy |

## Dependencies

- **External:** Anthropic, Cloudflare R2, Meta Graph (FB+IG), YouTube Data v3, TikTok API, Railway (deploy + `/data` volume)
- **Internal:** standalone — does NOT import from `tools/shared/` or `tools/enriquez2.0/`
- **Stack:** Next.js 16.2.4, React 19.2.4, TypeScript 5, better-sqlite3, AWS SDK S3 client (R2), Anthropic SDK, recharts, dnd-kit, Tailwind 4

## Production

- **Deployed:** `https://content-hub-production-b28e.up.railway.app`
- **Branch:** `main` — Railway deploys from GitHub on push
- **DB persistence:** Railway `/data` volume

## Last verified

2026-04-25 @ 3774fb5
