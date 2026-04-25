# Content Workflow

How a single content project flows from idea to posted, with every stage tracked in Content Hub.

## Lifecycle (auto-computed via `v_project_status` view)

```
draft → scripted → filming → editing → ready → scheduled → posted → archived
```

Allen never sets project status manually. The view derives it from children:

| Status | Trigger |
|---|---|
| `draft` | `ideas` row exists, no scripts yet |
| `scripted` | Any `scripts.idea_id = project_id` row exists |
| `editing` | `assets.status = 'editing'` (CapCut export landed) |
| `animating` | `assets.status = 'animating'` (`/scene-animation` started) |
| `ready` | `assets.status = 'ready'` (rendered MP4 in R2 `ready/`) |
| `scheduled` | `schedule.asset_id` references a project asset |
| `posted` | Any successful `posts` row references a project asset |
| `archived` | `ideas.archived = 1` (manual override via Kanban drag) |

## Entry points (4 ways a project starts)

| Source | UI action | Backend |
|---|---|---|
| **Raw idea** | Studio → Ideation → Notes → "Promote to project" | `POST /api/projects/from-note` |
| **Competitor post** | Inspiration → creator feed row → "Create project" | `POST /api/projects/from-source` (`source_table=creator_posts`) |
| **Viral reference** | Inspiration → viral refs row → "Create project" | `POST /api/projects/from-source` (`source_table=learning_refs`) |
| **Trending topic** | Inspiration → trending row → "Create project" | `POST /api/projects/from-source` (`source_table=learning_refs`) |

The `projects.source_type` + `source_ref_table` + `source_ref_id` columns trace each project back to its inspiration. Project cards show a "Modeled after @creator" badge when `source_type != 'raw'`.

## The full flow

```
[1] Idea seed (4 entry points above)
       │
       ▼
[2] INSERT projects row (id=N, source_type, source_ref_*, source_url)
       Kanban column: Draft
       │
       ▼
[3] Generate scripts (reel + youtube + carousel + per-platform captions)
       INSERT scripts rows (project_id=N)
       Kanban column: Scripted
       │
       ▼
[4] Film talking-head + edit in CapCut → export .mov
       Optional ping: POST /api/projects/N/state {phase: 'editing'}
       Kanban column: Editing
       │
       ▼
[5] /scene-animation builds GSAP scenes; preview at localhost:3002?comp=<id>
       Optional ping: POST /api/projects/N/state {phase: 'animating'}
       Kanban column: Animating
       │
       ▼
[6] /short-form-video composes face + scenes + captions, renders MP4
       Step 5.5: POST /api/library/promote {local_path, project_id, script_id}
       → Uploads to r2://content-hub/ready/<project_id>/<asset_id>-<slug>.mp4
       → INSERT assets row (status='ready', idea_id=project_id, script_id)
       Kanban column: Ready
       │
       ▼
[7] (optional) Schedule in /calendar
       INSERT schedule row (script_id, asset_id, slot_date)
       Kanban column: Scheduled
       │
       ▼
[8] Post via /library/[id] → "Post to Instagram" / YT / TikTok / FB
       Each platform returns its native ID (media_id, video_id, post_id)
       POST /api/posts {asset_id, platform, platform_post_id, platform_meta}
       → R2 key renamed: ready/<id>/... → posted/<yyyy-mm>/...
       → assets.status = 'posted'
       Kanban column: Posted
       │
       ▼
[9] Cron pulls per-platform analytics
       instagram_posts.post_id matches posts.platform_post_id (clean join)
       Roll-up shown on project card
```

## Skill choreography

| Skill | When | Touches Content Hub? |
|---|---|---|
| `/content` | Plan posts for the week | Reads ideas, schedule |
| `/content-research` | Find viral hooks/competitors | Writes learning_refs, creator_posts |
| `/scene-animation` | Build a single scene | Optional state ping (`animating`) |
| `/short-form-video` | Compose + render full reel | **Promotes to /api/library/promote on render** |
| `/carousel` | Convert reel → 1080×1350 slides | Reads transcript, writes assets |
| `/short-form-video → /carousel` | Auto-handoff after reel approval | `video-projects/<slug>/carousel_brief.json` |

## Foolproofing rules

- **Every script in DB has a `project_id`.** Period.
- **Every asset in DB has a `project_id`.** Orphans flagged in Library "Unlinked" filter.
- **Every post has a `platform_post_id`.** No URL-parsing joins to analytics tables.
- **`/short-form-video` Step 5.5 is mandatory** after final render approval — it's what links the MP4 back to the script.
- **Renames in R2** (`ready/` → `posted/`) happen automatically on first successful post.
