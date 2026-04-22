import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";
import {
  DEFAULT_RESEARCH_FILES,
  readLearning,
  type LearningItem,
} from "../lib/importers/learning";

export interface LearningSeedResult {
  viralRefsInserted: number;
  trendingTopicsInserted: number;
  competitorPostsInserted: number;
  totalLearningAfter: number;
}

// Idempotent upsert by (title, category) — title is the natural key for viral_refs
// and trending_topics; for competitor_post we use creator as title too.
export function seedLearning(dbPath?: string): LearningSeedResult {
  const ROOT = dbPath ? path.dirname(dbPath) : process.cwd();
  const DB_PATH = dbPath ?? path.join(ROOT, "content_hub.db");
  const SCHEMA_PATH = path.join(ROOT, "lib", "schema.sql");

  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");

  if (fs.existsSync(SCHEMA_PATH)) {
    db.exec(fs.readFileSync(SCHEMA_PATH, "utf8"));
  }

  const parsed = readLearning(DEFAULT_RESEARCH_FILES);

  const findRow = db.prepare<[string, string]>(
    `SELECT id FROM learning_refs WHERE COALESCE(title,'') = ? AND category = ?`,
  );
  const insertRow = db.prepare(
    `INSERT INTO learning_refs (url, creator, platform, category, title, notes)
     VALUES (@url, @creator, @platform, @category, @title, @notes)`,
  );
  const updateRow = db.prepare(
    `UPDATE learning_refs SET url = @url, creator = @creator, platform = @platform, notes = @notes WHERE id = @id`,
  );

  let viralRefsInserted = 0;
  let trendingTopicsInserted = 0;
  let competitorPostsInserted = 0;

  const upsert = (item: LearningItem) => {
    const titleKey = (item.title ?? "").trim();
    if (!titleKey) return false;
    const row = findRow.get(titleKey, item.category) as { id: number } | undefined;
    const payload = {
      url: item.url ?? null,
      creator: item.creator ?? null,
      platform: item.platform ?? null,
      category: item.category,
      title: titleKey,
      notes: item.notes ?? null,
    };
    if (row) {
      updateRow.run({ ...payload, id: row.id });
      return false;
    } else {
      insertRow.run(payload);
      return true;
    }
  };

  const tx = db.transaction(() => {
    for (const item of parsed.viralRefs) {
      if (upsert(item)) viralRefsInserted += 1;
    }
    for (const item of parsed.trendingTopics) {
      if (upsert(item)) trendingTopicsInserted += 1;
    }
    for (const item of parsed.competitorPosts) {
      if (upsert(item)) competitorPostsInserted += 1;
    }
  });
  tx();

  const totalLearningAfter = (
    db.prepare(`SELECT COUNT(*) as c FROM learning_refs`).get() as { c: number }
  ).c;

  db.close();

  return {
    viralRefsInserted,
    trendingTopicsInserted,
    competitorPostsInserted,
    totalLearningAfter,
  };
}

// CLI entrypoint
if (import.meta.url === `file://${process.argv[1]}`) {
  const result = seedLearning();
  console.log("[seed-learning]", result);
}
