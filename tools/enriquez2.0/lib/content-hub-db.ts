import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "./env.js";

const DB_PATH = path.join(REPO_ROOT, "tools", "content-hub", "content_hub.db");

export interface ScheduleRow {
  id: number;
  slot_date: string;
  slot_type: string;
  pillar: string | null;
  status: string;
  notes: string | null;
  script_id: number | null;
  asset_id: number | null;
  idea_title: string | null;
}

export interface PostRow {
  id: number;
  platform: string;
  posted_at: string | null;
  url: string | null;
  asset_title: string | null;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface IdeaRow {
  id: number;
  title: string;
  pillar: string | null;
  lane: string | null;
  status: string;
  archived: number;
  day_of_week: string | null;
  created_at: string;
}

export function dbExists(): boolean {
  return fs.existsSync(DB_PATH);
}

export function openReadOnly(): Database.Database {
  return new Database(DB_PATH, { readonly: true, fileMustExist: true });
}

export function getSchedule(db: Database.Database, fromDate: string, toDate: string): ScheduleRow[] {
  const rows = db
    .prepare(
      `SELECT s.id, s.slot_date, s.slot_type, s.pillar, s.status, s.notes,
              s.script_id, s.asset_id,
              i.title AS idea_title
         FROM schedule s
         LEFT JOIN scripts sc ON sc.id = s.script_id
         LEFT JOIN ideas i ON i.id = sc.idea_id
         WHERE s.slot_date >= ? AND s.slot_date <= ?
         ORDER BY s.slot_date ASC, s.slot_type ASC`,
    )
    .all(fromDate, toDate) as ScheduleRow[];
  return rows;
}

export function getPostsLast30d(db: Database.Database): PostRow[] {
  const cutoff = new Date(Date.now() - 30 * 86400_000).toISOString();
  const rows = db
    .prepare(
      `SELECT p.id, p.platform, p.posted_at, p.url,
              a.title AS asset_title,
              COALESCE(MAX(m.views), 0)    AS views,
              COALESCE(MAX(m.likes), 0)    AS likes,
              COALESCE(MAX(m.comments), 0) AS comments,
              COALESCE(MAX(m.shares), 0)   AS shares
         FROM posts p
         LEFT JOIN assets a ON a.id = p.asset_id
         LEFT JOIN metrics m ON m.post_id = p.id
         WHERE p.posted_at IS NOT NULL AND p.posted_at >= ?
         GROUP BY p.id
         ORDER BY p.posted_at DESC`,
    )
    .all(cutoff) as PostRow[];
  return rows;
}

export function getActiveIdeas(db: Database.Database): IdeaRow[] {
  const rows = db
    .prepare(
      `SELECT id, title, pillar, lane, status, archived, day_of_week, created_at
         FROM ideas
         WHERE archived = 0
         ORDER BY created_at DESC
         LIMIT 50`,
    )
    .all() as IdeaRow[];
  return rows;
}
