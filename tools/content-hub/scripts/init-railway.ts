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
