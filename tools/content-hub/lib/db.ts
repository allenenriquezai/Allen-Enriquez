import Database from "better-sqlite3";
import fs from "fs";
import path from "path";

let _instance: Database.Database | null = null;

function getInstance(): Database.Database {
  if (!_instance) {
    const DB_PATH =
      process.env.DATABASE_PATH ?? path.join(process.cwd(), "content_hub.db");
    const dir = path.dirname(DB_PATH);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    _instance = new Database(DB_PATH);
    _instance.pragma("journal_mode = WAL");
    _instance.prepare(
      `DELETE FROM schedule WHERE slot_date IN ('2026-04-16', '2026-04-17')`
    ).run();

    // Migrate assets table — add url + idea_id columns if missing
    const assetInfo = _instance.prepare("PRAGMA table_info(assets)").all() as { name: string }[];
    if (assetInfo.length > 0) {
      const cols = new Set(assetInfo.map((c) => c.name));
      if (!cols.has("url")) {
        _instance.exec("ALTER TABLE assets ADD COLUMN url TEXT");
      }
      if (!cols.has("idea_id")) {
        _instance.exec("ALTER TABLE assets ADD COLUMN idea_id INTEGER");
      }
    }

    // Migrate schedule table — add asset_id column if missing
    const schedInfo = _instance.prepare("PRAGMA table_info(schedule)").all() as { name: string }[];
    if (schedInfo.length > 0) {
      const cols = new Set(schedInfo.map((c) => c.name));
      if (!cols.has("asset_id")) {
        _instance.exec("ALTER TABLE schedule ADD COLUMN asset_id INTEGER");
      }
    }

    // Migrate inbox table — add columns if missing
    const inboxInfo = _instance.prepare("PRAGMA table_info(inbox)").all() as { name: string }[];
    if (inboxInfo.length > 0) {
      const cols = new Set(inboxInfo.map((c) => c.name));
      if (!cols.has("external_id")) {
        _instance.exec("ALTER TABLE inbox ADD COLUMN external_id TEXT");
        _instance.exec(
          "CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_external ON inbox(platform, external_id) WHERE external_id IS NOT NULL",
        );
      }
      if (!cols.has("post_id")) {
        _instance.exec("ALTER TABLE inbox ADD COLUMN post_id TEXT");
      }
      if (!cols.has("reply_sent")) {
        _instance.exec("ALTER TABLE inbox ADD COLUMN reply_sent INTEGER DEFAULT 0");
      }
    }

    // OAuth tokens for YouTube and TikTok
    _instance.exec(`
      CREATE TABLE IF NOT EXISTS oauth_tokens (
        platform TEXT PRIMARY KEY,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        expires_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `);

    _instance.exec(`
      CREATE TABLE IF NOT EXISTS tiktok_stats (
        video_id TEXT PRIMARY KEY,
        title TEXT,
        view_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        comment_count INTEGER DEFAULT 0,
        share_count INTEGER DEFAULT 0,
        published_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }
  return _instance;
}

// Lazy proxy — DB only opens on first method call (safe at build time)
export default new Proxy({} as Database.Database, {
  get(_target, prop) {
    return (getInstance() as any)[prop as any];
  },
}) as Database.Database;
