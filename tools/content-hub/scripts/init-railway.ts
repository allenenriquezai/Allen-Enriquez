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
