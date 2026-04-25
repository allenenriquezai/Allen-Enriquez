-- "ideas" is the project root. UI surfaces it as "Project". Same table.
CREATE TABLE IF NOT EXISTS ideas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  hook TEXT,
  pillar TEXT,
  lane TEXT,
  category TEXT,
  modeled_after TEXT,
  source_platform TEXT,
  source_url TEXT,
  status TEXT DEFAULT 'new',  -- new, picked, dismissed, bookmarked (legacy ideation status; project lifecycle lives in v_project_status view)
  day_of_week TEXT,
  slot INTEGER,
  batch TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  notes TEXT, -- reviewer notes
  theme TEXT,
  archived INTEGER DEFAULT 0, -- project archived flag
  source_type TEXT DEFAULT 'raw', -- raw, competitor_post, viral_ref, trending
  source_ref_table TEXT, -- creator_posts | learning_refs (when source_type != 'raw')
  source_ref_id INTEGER  -- FK into source_ref_table
);

CREATE TABLE IF NOT EXISTS scripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id INTEGER REFERENCES ideas(id),
  variant TEXT NOT NULL, -- reel (UI: short-form), youtube (UI: long-form), carousel, caption_fb, caption_ig, caption_tiktok, caption_yt, caption_x
  body TEXT NOT NULL,
  word_count INTEGER,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id INTEGER REFERENCES scripts(id),
  asset_id INTEGER REFERENCES assets(id),
  slot_date TEXT NOT NULL, -- YYYY-MM-DD
  slot_type TEXT NOT NULL, -- reel_1, reel_2, youtube, fb_post, carousel
  pillar TEXT,
  status TEXT DEFAULT 'planned', -- planned, scripted, filmed, edited, posted
  notes TEXT,
  captions_json TEXT -- per-platform caption overrides: { caption_fb, caption_ig, caption_tiktok, caption_yt }
);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, -- reel (UI: short-form), youtube (UI: long-form), carousel, thumbnail
  title TEXT,
  url TEXT,            -- R2 public URL (set after upload)
  thumbnail_url TEXT,  -- custom thumbnail URL (optional override for video first-frame)
  duration_seconds INTEGER, -- video duration; null for carousels
  idea_id INTEGER REFERENCES ideas(id),  -- project FK (UI: project)
  script_id INTEGER REFERENCES scripts(id),
  variant_label TEXT,  -- e.g. "v5", "draft", "final" — parsed from filename
  hidden INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ready',     -- editing, animating, ready, posted, archived
  local_path TEXT,                 -- filesystem path on creator's machine when first rendered
  render_meta_json TEXT,           -- skill metadata: composition_id, scene_count, audio_duration
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER REFERENCES assets(id),
  platform TEXT NOT NULL, -- facebook, instagram, tiktok, youtube, x
  posted_at TEXT,
  url TEXT,
  platform_post_id TEXT,        -- IG media_id, YT video_id, TikTok video_id, FB post_id
  platform_meta_json TEXT,      -- raw API response for debugging
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
-- idx_posts_platform_id created in init-railway.ts after ALTER TABLE migration

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER REFERENCES posts(id),
  views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  follows_gained INTEGER DEFAULT 0,
  recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  thread_type TEXT DEFAULT 'comment', -- comment, dm, mention
  author TEXT,
  thread_text TEXT NOT NULL,
  reply_text TEXT,
  status TEXT DEFAULT 'new', -- new, replied, ignored, escalated
  received_at TEXT DEFAULT CURRENT_TIMESTAMP,
  external_id TEXT,
  post_id TEXT,
  reply_sent INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_external ON inbox(platform, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS learning_refs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT,
  creator TEXT,
  platform TEXT,
  category TEXT DEFAULT 'viral_ref', -- viral_ref, trending_topic, competitor_post
  title TEXT,
  notes TEXT,
  saved_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creator_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT NOT NULL UNIQUE,
  creator TEXT NOT NULL,
  platform TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT,
  description TEXT,
  thumbnail_url TEXT,
  posted_at TEXT,
  view_count INTEGER,
  like_count INTEGER,
  comment_count INTEGER,
  duration_sec INTEGER,
  transcript TEXT,
  hook TEXT,
  topic TEXT,
  why_it_works TEXT,
  raw_meta_json TEXT,
  fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_creator_posts_posted_at ON creator_posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_creator_posts_creator ON creator_posts(creator);
CREATE INDEX IF NOT EXISTS idx_creator_posts_fetched_at ON creator_posts(fetched_at DESC);

CREATE TABLE IF NOT EXISTS facebook_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT NOT NULL UNIQUE,
  message TEXT,
  created_time TEXT,
  permalink_url TEXT,
  impressions INTEGER DEFAULT 0,
  reach INTEGER DEFAULT 0,
  engaged_users INTEGER DEFAULT 0,
  reactions INTEGER DEFAULT 0,
  comments_count INTEGER DEFAULT 0,
  shares_count INTEGER DEFAULT 0,
  fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fb_posts_created ON facebook_posts(created_time DESC);

CREATE TABLE IF NOT EXISTS instagram_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT NOT NULL UNIQUE,
  caption TEXT,
  media_type TEXT,
  timestamp TEXT,
  permalink TEXT,
  like_count INTEGER DEFAULT 0,
  comments_count INTEGER DEFAULT 0,
  impressions INTEGER DEFAULT 0,
  reach INTEGER DEFAULT 0,
  saved INTEGER DEFAULT 0,
  fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ig_posts_ts ON instagram_posts(timestamp DESC);

CREATE TABLE IF NOT EXISTS tiktok_stats (
  video_id TEXT PRIMARY KEY,
  title TEXT,
  view_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  comment_count INTEGER DEFAULT 0,
  share_count INTEGER DEFAULT 0,
  published_at TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
  platform TEXT PRIMARY KEY,
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  expires_at TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ideation_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT,
  tags TEXT,           -- comma-separated: psychology,editing,hooks,frameworks
  author TEXT,         -- allen, wife, claude
  pinned INTEGER DEFAULT 0,
  idea_id INTEGER REFERENCES ideas(id), -- pinned to a project (nullable; UI shows under that project's Notes tab)
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ideation_notes_updated ON ideation_notes(updated_at DESC);
-- idx_ideation_notes_idea created in init-railway.ts after ALTER TABLE migration

CREATE TABLE IF NOT EXISTS week_themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start TEXT NOT NULL,
  day_of_week TEXT NOT NULL,
  theme TEXT NOT NULL,
  pillar TEXT,
  notes TEXT,
  ideas_generated INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_week_themes_day ON week_themes(week_start, day_of_week);

CREATE TABLE IF NOT EXISTS ideation_tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS youtube_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL UNIQUE,
  title TEXT,
  url TEXT NOT NULL,
  published_at TEXT,
  views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_youtube_stats_published_at ON youtube_stats(published_at DESC);

-- Project lifecycle indexes (idx_assets_status / idx_assets_idea / idx_assets_script
-- created in init-railway.ts after ALTER TABLE migration since the columns are added
-- by migration on existing DBs)

-- v_project_status view: created in init-railway.ts AFTER column ALTERs
-- so the view definition can reference assets.status / ideas.archived which
-- only exist post-migration on existing DBs.
