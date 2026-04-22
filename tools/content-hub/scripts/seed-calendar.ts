import path from "node:path";
import Database from "better-sqlite3";
import { importTracker } from "../lib/importers/tracker";
import { importVideos } from "../lib/importers/videos";

export function seedCalendar(): void {
  const DB_PATH = path.join(process.cwd(), "content_hub.db");
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");

  try {
    const trackerResult = importTracker(db);
    console.log(
      `[seed-calendar] schedule: ${trackerResult.inserted} inserted, ${trackerResult.updated} updated, ${trackerResult.skipped} skipped (empty topic), ${trackerResult.total} rows with topic`,
    );

    const videoResult = importVideos(db);
    console.log(
      `[seed-calendar] assets: ${videoResult.inserted} inserted, ${videoResult.updated} updated, ${videoResult.total} total mp4s`,
    );
    for (const p of videoResult.paths) {
      console.log(`  - ${p}`);
    }
  } finally {
    db.close();
  }
}

// Run directly when invoked as: tsx scripts/seed-calendar.ts
const invokedDirectly =
  typeof process !== "undefined" &&
  process.argv[1] &&
  /seed-calendar\.ts$/.test(process.argv[1]);
if (invokedDirectly) {
  seedCalendar();
}
