import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";
import {
  DEFAULT_DRAFTS_PATH,
  readDrafts,
  mapTypeToVariant,
  countWords,
} from "../lib/importers/drafts";
import {
  DEFAULT_RESEARCH_PATH,
  readResearch,
} from "../lib/importers/research";

export interface SeedResult {
  ideasInserted: number;
  scriptsInserted: number;
  researchIdeasInserted: number;
  totalIdeasAfter: number;
  totalScriptsAfter: number;
}

// Idempotent: upsert ideas by (title, batch) tuple.
// If an existing idea with same (title, batch) is found, reuse it. We then
// upsert the script by (idea_id, variant).
export function seedIdeation(dbPath?: string): SeedResult {
  const ROOT = dbPath ? path.dirname(dbPath) : process.cwd();
  const DB_PATH = dbPath ?? path.join(ROOT, "content_hub.db");
  const SCHEMA_PATH = path.join(ROOT, "lib", "schema.sql");

  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");

  // Make sure tables exist (safe no-op if already migrated).
  if (fs.existsSync(SCHEMA_PATH)) {
    db.exec(fs.readFileSync(SCHEMA_PATH, "utf8"));
  }

  const drafts = readDrafts(DEFAULT_DRAFTS_PATH);
  const research = readResearch(DEFAULT_RESEARCH_PATH);

  const findIdea = db.prepare<[string, string | null]>(
    `SELECT id FROM ideas WHERE title = ? AND COALESCE(batch,'') = COALESCE(?, '')`,
  );
  const insertIdea = db.prepare(
    `INSERT INTO ideas (title, pillar, lane, category, modeled_after, source_platform, day_of_week, slot, batch, status)
     VALUES (@title, @pillar, @lane, @category, @modeled_after, @source_platform, @day_of_week, @slot, @batch, @status)`,
  );

  const findScript = db.prepare<[number, string]>(
    `SELECT id FROM scripts WHERE idea_id = ? AND variant = ?`,
  );
  const insertScript = db.prepare(
    `INSERT INTO scripts (idea_id, variant, body, word_count, updated_at)
     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
  );
  const updateScript = db.prepare(
    `UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
  );

  let ideasInserted = 0;
  let scriptsInserted = 0;
  let researchIdeasInserted = 0;

  const tx = db.transaction(() => {
    // 1) Drafts → ideas + scripts
    for (const d of drafts) {
      const title = (d.title ?? "").trim();
      if (!title) continue;
      const batch = d.batch ?? null;

      let ideaId: number;
      const existing = findIdea.get(title, batch) as
        | { id: number }
        | undefined;
      if (existing) {
        ideaId = existing.id;
      } else {
        const info = insertIdea.run({
          title,
          pillar: d.category ?? null,
          lane: d.lane ?? null,
          category: d.category ?? null,
          modeled_after: d.modeled_after ?? null,
          source_platform: null,
          day_of_week: d.day ?? null,
          slot: d.slot ?? null,
          batch,
          status: "new",
        });
        ideaId = Number(info.lastInsertRowid);
        ideasInserted += 1;
      }

      const variant = mapTypeToVariant(d.type ?? "reel");
      const body = d.script ?? "";
      const wc = d.word_count ?? countWords(body);
      const existingScript = findScript.get(ideaId, variant) as
        | { id: number }
        | undefined;
      if (existingScript) {
        updateScript.run(body, wc, existingScript.id);
      } else {
        insertScript.run(ideaId, variant, body, wc);
        scriptsInserted += 1;
      }
    }

    // 2) Research "Recommended Hooks for Allen (adapted)" → ideas only.
    for (const hook of research.recommendedHooks) {
      const title = hook.trim();
      if (!title) continue;
      const batch = "research";
      const existing = findIdea.get(title, batch) as
        | { id: number }
        | undefined;
      if (existing) continue;
      insertIdea.run({
        title,
        pillar: "research",
        lane: null,
        category: null,
        modeled_after: null,
        source_platform: "research",
        day_of_week: null,
        slot: null,
        batch,
        status: "new",
      });
      researchIdeasInserted += 1;
    }
  });

  tx();

  const totalIdeasAfter = (
    db.prepare(`SELECT COUNT(*) as c FROM ideas`).get() as { c: number }
  ).c;
  const totalScriptsAfter = (
    db.prepare(`SELECT COUNT(*) as c FROM scripts`).get() as { c: number }
  ).c;

  db.close();

  return {
    ideasInserted,
    scriptsInserted,
    researchIdeasInserted,
    totalIdeasAfter,
    totalScriptsAfter,
  };
}

// CLI entrypoint
if (import.meta.url === `file://${process.argv[1]}`) {
  const result = seedIdeation();
  console.log("[seed-ideation]", result);
}
