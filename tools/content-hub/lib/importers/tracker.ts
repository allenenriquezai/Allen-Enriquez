import fs from "node:fs";
import path from "node:path";
import type Database from "better-sqlite3";

const TRACKER_PATH =
  "/Users/allenenriquez/Developer/Allen-Enriquez/projects/personal/.tmp/content_tracker.json";

type SlotState = {
  topic?: string;
  script?: string;
  filmed?: string;
  posted?: string;
};

type Day = {
  day: number;
  date: string;
  reel_1?: SlotState;
  reel_2?: SlotState;
  youtube?: SlotState;
  fb_posts?: unknown[];
};

type Tracker = {
  campaign: string;
  start_date: string;
  total_days: number;
  days: Day[];
};

type SlotType = "reel_1" | "reel_2" | "youtube";

function deriveStatus(slot: SlotState): string {
  if (slot.posted === "posted") return "posted";
  if (slot.filmed === "filmed") return "filmed";
  if (slot.script === "written") return "scripted";
  return "planned";
}

export type ImportTrackerResult = {
  inserted: number;
  updated: number;
  skipped: number;
  total: number;
};

/**
 * Idempotent upsert by (slot_date, slot_type). Only writes rows for slots with
 * a non-empty topic. Leaves script_id NULL (linked later when a script is
 * dragged onto the day).
 */
export function importTracker(db: Database.Database): ImportTrackerResult {
  if (!fs.existsSync(TRACKER_PATH)) {
    console.warn(`[tracker] missing file: ${TRACKER_PATH}`);
    return { inserted: 0, updated: 0, skipped: 0, total: 0 };
  }

  const raw = fs.readFileSync(TRACKER_PATH, "utf8");
  const data = JSON.parse(raw) as Tracker;

  const findStmt = db.prepare(
    "SELECT id FROM schedule WHERE slot_date = ? AND slot_type = ?",
  );
  const insertStmt = db.prepare(
    `INSERT INTO schedule (slot_date, slot_type, pillar, status, notes)
     VALUES (?, ?, NULL, ?, ?)`,
  );
  const updateStmt = db.prepare(
    "UPDATE schedule SET status = ?, notes = ? WHERE id = ?",
  );

  const slotTypes: SlotType[] = ["reel_1", "reel_2", "youtube"];
  let inserted = 0;
  let updated = 0;
  let skipped = 0;
  let total = 0;

  const tx = db.transaction(() => {
    for (const day of data.days ?? []) {
      for (const slotType of slotTypes) {
        const slot = day[slotType];
        if (!slot) continue;
        const topic = (slot.topic ?? "").trim();
        if (!topic) {
          skipped += 1;
          continue;
        }
        total += 1;
        const status = deriveStatus(slot);
        const existing = findStmt.get(day.date, slotType) as
          | { id: number }
          | undefined;
        if (existing) {
          updateStmt.run(status, topic, existing.id);
          updated += 1;
        } else {
          insertStmt.run(day.date, slotType, status, topic);
          inserted += 1;
        }
      }
    }
  });
  tx();

  return { inserted, updated, skipped, total };
}

export const __TRACKER_PATH = TRACKER_PATH;
export const __path = path;
