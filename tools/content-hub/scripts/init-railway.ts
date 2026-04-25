import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

const ROOT = process.cwd();
const DB_PATH =
  process.env.DATABASE_PATH ?? path.join(ROOT, "content_hub.db");
const SCHEMA_PATH = path.join(ROOT, "lib", "schema.sql");
const SEED_PATH = path.join(ROOT, "scripts", "seed-data.sql");

// Ensure parent directory exists (for volume mounts like /data)
const dir = path.dirname(DB_PATH);
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

// Always run schema (idempotent — all CREATE TABLE IF NOT EXISTS)
const schema = fs.readFileSync(SCHEMA_PATH, "utf8");
db.exec(schema);
console.log(`[init] Schema applied → ${DB_PATH}`);

// Column migrations — safe to run every boot
type ColInfo = { name: string };
const ideaCols = (db.prepare("PRAGMA table_info(ideas)").all() as ColInfo[]).map(c => c.name);
if (!ideaCols.includes("notes")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN notes TEXT").run();
  console.log("[init] Migration: added notes column to ideas");
}

const inboxCols = (db.prepare("PRAGMA table_info(inbox)").all() as ColInfo[]).map(c => c.name);
if (!inboxCols.includes("external_id")) {
  db.prepare("ALTER TABLE inbox ADD COLUMN external_id TEXT").run();
  console.log("[init] Migration: added external_id column to inbox");
}
if (!inboxCols.includes("post_id")) {
  db.prepare("ALTER TABLE inbox ADD COLUMN post_id TEXT").run();
  console.log("[init] Migration: added post_id column to inbox");
}
if (!inboxCols.includes("reply_sent")) {
  db.prepare("ALTER TABLE inbox ADD COLUMN reply_sent INTEGER DEFAULT 0").run();
  console.log("[init] Migration: added reply_sent column to inbox");
}
db.exec(`CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_external ON inbox(platform, external_id) WHERE external_id IS NOT NULL`);

if (!ideaCols.includes("theme")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN theme TEXT").run();
  console.log("[init] Migration: added theme column to ideas");
}

// Project lifecycle: ideas as projects (same table; UI says "project")
if (!ideaCols.includes("archived")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN archived INTEGER DEFAULT 0").run();
  console.log("[init] Migration: added archived column to ideas");
}
if (!ideaCols.includes("source_type")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN source_type TEXT DEFAULT 'raw'").run();
  console.log("[init] Migration: added source_type column to ideas");
}
if (!ideaCols.includes("source_ref_table")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN source_ref_table TEXT").run();
  console.log("[init] Migration: added source_ref_table column to ideas");
}
if (!ideaCols.includes("source_ref_id")) {
  db.prepare("ALTER TABLE ideas ADD COLUMN source_ref_id INTEGER").run();
  console.log("[init] Migration: added source_ref_id column to ideas");
}

const assetCols = (db.prepare("PRAGMA table_info(assets)").all() as ColInfo[]).map(c => c.name);
if (!assetCols.includes("hidden")) {
  db.prepare("ALTER TABLE assets ADD COLUMN hidden INTEGER DEFAULT 0").run();
  console.log("[init] Migration: added hidden column to assets");
}
if (!assetCols.includes("variant_label")) {
  db.prepare("ALTER TABLE assets ADD COLUMN variant_label TEXT").run();
  console.log("[init] Migration: added variant_label column to assets");
}
if (!assetCols.includes("status")) {
  db.prepare("ALTER TABLE assets ADD COLUMN status TEXT DEFAULT 'ready'").run();
  console.log("[init] Migration: added status column to assets");
}
if (!assetCols.includes("script_id")) {
  db.prepare("ALTER TABLE assets ADD COLUMN script_id INTEGER REFERENCES scripts(id)").run();
  console.log("[init] Migration: added script_id column to assets");
}
if (!assetCols.includes("local_path")) {
  db.prepare("ALTER TABLE assets ADD COLUMN local_path TEXT").run();
  console.log("[init] Migration: added local_path column to assets");
}
if (!assetCols.includes("render_meta_json")) {
  db.prepare("ALTER TABLE assets ADD COLUMN render_meta_json TEXT").run();
  console.log("[init] Migration: added render_meta_json column to assets");
}

// Backfill assets.status: 'posted' if a post row references it; else leave default 'ready'
db.exec(`
  UPDATE assets SET status='posted'
  WHERE id IN (SELECT DISTINCT asset_id FROM posts WHERE asset_id IS NOT NULL)
    AND status != 'posted'
`);

const postCols = (db.prepare("PRAGMA table_info(posts)").all() as ColInfo[]).map(c => c.name);
if (!postCols.includes("platform_post_id")) {
  db.prepare("ALTER TABLE posts ADD COLUMN platform_post_id TEXT").run();
  console.log("[init] Migration: added platform_post_id column to posts");
}
if (!postCols.includes("platform_meta_json")) {
  db.prepare("ALTER TABLE posts ADD COLUMN platform_meta_json TEXT").run();
  console.log("[init] Migration: added platform_meta_json column to posts");
}

const noteCols = (db.prepare("PRAGMA table_info(ideation_notes)").all() as ColInfo[]).map(c => c.name);
if (!noteCols.includes("idea_id")) {
  db.prepare("ALTER TABLE ideation_notes ADD COLUMN idea_id INTEGER REFERENCES ideas(id)").run();
  console.log("[init] Migration: added idea_id column to ideation_notes");
}

// Indexes for the new columns
db.exec(`
  CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
  CREATE INDEX IF NOT EXISTS idx_assets_idea ON assets(idea_id);
  CREATE INDEX IF NOT EXISTS idx_assets_script ON assets(script_id);
  CREATE INDEX IF NOT EXISTS idx_posts_platform_id ON posts(platform, platform_post_id);
  CREATE INDEX IF NOT EXISTS idx_ideation_notes_idea ON ideation_notes(idea_id);
`);

// Computed project status view — derives from children, never set manually.
// Status order: archived > posted > scheduled > ready > editing > filming > scripted > draft.
// 'filming' + 'editing' can be advanced via /api/projects/[id]/state phase ping
// (writes a stub assets row with status=phase) so the Kanban card slides without
// waiting for a real render to land.
db.exec(`
  DROP VIEW IF EXISTS v_project_status;
  CREATE VIEW v_project_status AS
  SELECT i.id AS project_id,
         CASE
           WHEN i.archived=1 THEN 'archived'
           WHEN EXISTS(SELECT 1 FROM posts po
                       JOIN assets a ON po.asset_id=a.id
                       WHERE a.idea_id=i.id AND po.status='success') THEN 'posted'
           WHEN EXISTS(SELECT 1 FROM schedule s
                       JOIN assets a ON s.asset_id=a.id
                       WHERE a.idea_id=i.id) THEN 'scheduled'
           WHEN EXISTS(SELECT 1 FROM assets a
                       WHERE a.idea_id=i.id AND a.status='ready') THEN 'ready'
           WHEN EXISTS(SELECT 1 FROM assets a
                       WHERE a.idea_id=i.id AND a.status='editing') THEN 'editing'
           WHEN EXISTS(SELECT 1 FROM assets a
                       WHERE a.idea_id=i.id AND a.status='filming') THEN 'filming'
           WHEN EXISTS(SELECT 1 FROM scripts s
                       WHERE s.idea_id=i.id) THEN 'scripted'
           ELSE 'draft'
         END AS status
  FROM ideas i;
`);
console.log("[init] Migration: refreshed v_project_status view");

// week_themes + ideation_tags (idempotent)
db.exec(`
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
`);

// Seed ideation_tags presets if empty
const tagCount = (db.prepare("SELECT COUNT(*) as n FROM ideation_tags").get() as { n: number }).n;
if (tagCount === 0) {
  const seedTags = ["psychology", "editing", "hooks", "frameworks", "tooling", "ops"];
  const insertTag = db.prepare("INSERT OR IGNORE INTO ideation_tags (name) VALUES (?)");
  for (const t of seedTags) insertTag.run(t);
  console.log(`[init] Seeded ${seedTags.length} ideation_tags presets`);
}

// Create youtube_stats if missing (schema handles IF NOT EXISTS, this is belt-and-suspenders)
const ytExists = db
  .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='youtube_stats'")
  .get();
if (!ytExists) {
  db.exec(`
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
  `);
  console.log("[init] Migration: created youtube_stats table");
}

// Seed only if ideas table is empty (first deploy on fresh volume)
const count = (
  db.prepare("SELECT COUNT(*) as n FROM ideas").get() as { n: number }
).n;

if (count === 0 && fs.existsSync(SEED_PATH)) {
  const seed = fs.readFileSync(SEED_PATH, "utf8");
  db.exec(seed);
  const seeded = (
    db.prepare("SELECT COUNT(*) as n FROM ideas").get() as { n: number }
  ).n;
  console.log(`[init] Seeded ${seeded} ideas from seed-data.sql`);
} else {
  console.log(`[init] DB has ${count} ideas — skipping seed`);
}

db.close();
