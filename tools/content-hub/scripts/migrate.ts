import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

const ROOT = process.cwd();
const DB_PATH = path.join(ROOT, "content_hub.db");
const SCHEMA_PATH = path.join(ROOT, "lib", "schema.sql");

const schema = fs.readFileSync(SCHEMA_PATH, "utf8");
const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");
db.exec(schema);

const tables = db
  .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
  .all() as Array<{ name: string }>;

console.log(`Migrated ${DB_PATH}`);
console.log("Tables:", tables.map((t) => t.name).join(", "));

db.close();
