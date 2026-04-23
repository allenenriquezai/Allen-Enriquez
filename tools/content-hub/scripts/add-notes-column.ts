/**
 * Migration: add `notes` column to the `ideas` table if it doesn't exist.
 *
 * Safe to run multiple times — it checks the column list before altering.
 * SQLite doesn't support IF NOT EXISTS on ALTER TABLE ADD COLUMN, so we
 * inspect PRAGMA table_info and skip if the column is already present.
 *
 * Usage:
 *   npx ts-node --esm scripts/add-notes-column.ts
 *   # or via the npm script defined in package.json:
 *   npm run migrate:notes
 */

import Database from "better-sqlite3";
import path from "node:path";

const ROOT = process.cwd();
const DB_PATH =
  process.env.DATABASE_PATH ?? path.join(ROOT, "content_hub.db");

const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

type ColumnInfo = { cid: number; name: string; type: string };

const columns = db
  .prepare("PRAGMA table_info(ideas)")
  .all() as ColumnInfo[];

const hasNotes = columns.some((c) => c.name === "notes");

if (hasNotes) {
  console.log("[add-notes-column] `notes` column already exists — skipping.");
} else {
  db.prepare("ALTER TABLE ideas ADD COLUMN notes TEXT").run();
  console.log("[add-notes-column] `notes TEXT` column added to `ideas`.");
}

db.close();
