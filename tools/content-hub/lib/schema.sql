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
  status TEXT DEFAULT 'new',  -- new, picked, dismissed, bookmarked
  day_of_week TEXT,
  slot INTEGER,
  batch TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  notes TEXT -- reviewer notes
);

CREATE TABLE IF NOT EXISTS scripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id INTEGER REFERENCES ideas(id),
  variant TEXT NOT NULL, -- reel, youtube, carousel, caption_fb, caption_ig, caption_tiktok, caption_yt, caption_x
  body TEXT NOT NULL,
  word_count INTEGER,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id INTEGER REFERENCES scripts(id),
  slot_date TEXT NOT NULL, -- YYYY-MM-DD
  slot_type TEXT NOT NULL, -- reel_1, reel_2, youtube, fb_post, carousel
  pillar TEXT,
  status TEXT DEFAULT 'planned', -- planned, scripted, filmed, edited, posted
  notes TEXT
);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, -- reel, youtube, carousel, thumbnail
  title TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER REFERENCES assets(id),
  platform TEXT NOT NULL, -- facebook, instagram, tiktok, youtube, x
  posted_at TEXT,
  url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

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
  received_at TEXT DEFAULT CURRENT_TIMESTAMP
);

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
