import path from "node:path";
import Database from "better-sqlite3";

const ROOT = process.cwd();
const DB_PATH = process.env.DATABASE_PATH ?? path.join(ROOT, "content_hub.db");

type Row = Record<string, unknown>;

const db = new Database(DB_PATH, { readonly: true });

function rule(label: string, sql: string, params: unknown[] = []): { label: string; count: number; sample: Row[] } {
  const count = (db.prepare(`SELECT COUNT(*) AS n FROM (${sql})`).get(...params) as { n: number }).n;
  const sample = count > 0 ? (db.prepare(sql + " LIMIT 5").all(...params) as Row[]) : [];
  return { label, count, sample };
}

const checks = [
  rule(
    "Assets with NULL idea_id (orphan from project)",
    "SELECT id, path, type, title, status FROM assets WHERE idea_id IS NULL AND (path IS NULL OR path NOT LIKE 'stub:%')",
  ),
  rule(
    "Assets with NULL script_id (no source script linked)",
    "SELECT id, path, type, title, idea_id FROM assets WHERE script_id IS NULL AND status IN ('ready','posted','editing','animating') AND path NOT LIKE 'stub:%'",
  ),
  rule(
    "Posts with NULL platform_post_id (analytics join broken)",
    "SELECT id, asset_id, platform, posted_at FROM posts WHERE platform_post_id IS NULL AND status = 'success'",
  ),
  rule(
    "Successful posts whose asset has stale status (not 'posted')",
    `SELECT po.id, po.asset_id, po.platform, a.status FROM posts po
       JOIN assets a ON po.asset_id = a.id
       WHERE po.status = 'success' AND a.status != 'posted'`,
  ),
  rule(
    "Projects with no scripts AND no assets (drafts)",
    `SELECT i.id, i.title, i.created_at FROM ideas i
       WHERE NOT EXISTS(SELECT 1 FROM scripts s WHERE s.idea_id = i.id)
         AND NOT EXISTS(SELECT 1 FROM assets a WHERE a.idea_id = i.id)`,
  ),
  rule(
    "R2 keys still in 'ready/' for posted assets (move did not run)",
    "SELECT id, path FROM assets WHERE status = 'posted' AND path LIKE 'ready/%'",
  ),
];

let total = 0;
console.log(`# Content Hub Integrity Report — ${new Date().toISOString()}`);
console.log(`DB: ${DB_PATH}\n`);

for (const c of checks) {
  total += c.count;
  const tag = c.count === 0 ? "OK" : "FLAG";
  console.log(`[${tag}] ${c.label}: ${c.count}`);
  if (c.sample.length > 0) {
    for (const row of c.sample) {
      console.log("       •", JSON.stringify(row));
    }
  }
}

db.close();

console.log(`\nTotal flagged rows: ${total}`);
process.exit(total > 0 ? 1 : 0);
