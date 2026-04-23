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
  }
  return _instance;
}

// Lazy proxy — DB only opens on first method call (safe at build time)
export default new Proxy({} as Database.Database, {
  get(_target, prop) {
    return (getInstance() as any)[prop as any];
  },
}) as Database.Database;
