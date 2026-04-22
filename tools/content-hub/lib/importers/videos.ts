import fs from "node:fs";
import path from "node:path";
import type Database from "better-sqlite3";

const VIDEOS_ROOT =
  "/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/videos";

export type ImportVideosResult = {
  inserted: number;
  updated: number;
  total: number;
  paths: string[];
};

function stripTitle(filename: string): string {
  const base = filename.replace(/\.mp4$/i, "");
  return base
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function walkMp4s(dir: string, out: string[], depth = 0, maxDepth = 3): void {
  if (depth > maxDepth) return;
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of entries) {
    if (e.name.startsWith(".")) continue;
    if (e.name === "node_modules") continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      walkMp4s(full, out, depth + 1, maxDepth);
    } else if (e.isFile() && /\.mp4$/i.test(e.name)) {
      out.push(full);
    }
  }
}

/**
 * Scans videos/ready and each reel project dir (root + render/ + renders/).
 * Dedups by absolute path. Upserts by path.
 */
export function importVideos(db: Database.Database): ImportVideosResult {
  const paths: string[] = [];
  if (!fs.existsSync(VIDEOS_ROOT)) {
    console.warn(`[videos] missing dir: ${VIDEOS_ROOT}`);
    return { inserted: 0, updated: 0, total: 0, paths };
  }

  // ready/
  const readyDir = path.join(VIDEOS_ROOT, "ready");
  if (fs.existsSync(readyDir)) {
    walkMp4s(readyDir, paths, 0, 1);
  }

  // each reel project subdir — scan root + render/ + renders/
  const subdirs = fs
    .readdirSync(VIDEOS_ROOT, { withFileTypes: true })
    .filter((e) => e.isDirectory() && e.name !== "ready");
  for (const sub of subdirs) {
    const subPath = path.join(VIDEOS_ROOT, sub.name);
    walkMp4s(subPath, paths, 0, 2);
  }

  // dedupe
  const unique = Array.from(new Set(paths));

  const findStmt = db.prepare("SELECT id, title FROM assets WHERE path = ?");
  const insertStmt = db.prepare(
    "INSERT INTO assets (path, type, title) VALUES (?, ?, ?)",
  );
  const updateStmt = db.prepare("UPDATE assets SET title = ? WHERE id = ?");

  let inserted = 0;
  let updated = 0;

  const tx = db.transaction(() => {
    for (const full of unique) {
      const title = stripTitle(path.basename(full));
      const type = "reel"; // all mp4s are treated as reels for now
      const existing = findStmt.get(full) as
        | { id: number; title: string | null }
        | undefined;
      if (existing) {
        if (existing.title !== title) {
          updateStmt.run(title, existing.id);
          updated += 1;
        }
      } else {
        insertStmt.run(full, type, title);
        inserted += 1;
      }
    }
  });
  tx();

  return { inserted, updated, total: unique.length, paths: unique };
}

export const __VIDEOS_ROOT = VIDEOS_ROOT;
