import { NextResponse } from "next/server";
import db from "@/lib/db";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

db.exec(`
  CREATE TABLE IF NOT EXISTS instagram_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL UNIQUE,
    caption TEXT,
    media_type TEXT,
    timestamp TEXT,
    permalink TEXT,
    like_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    saved INTEGER DEFAULT 0,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX IF NOT EXISTS idx_ig_posts_ts ON instagram_posts(timestamp DESC);
`);

async function fetchInsights(mediaId: string): Promise<{ impressions: number; reach: number; saved: number }> {
  const url = new URL(`${IG_BASE}/${mediaId}/insights`);
  url.searchParams.set("metric", "impressions,reach,saved");
  url.searchParams.set("access_token", IG_TOKEN);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) return { impressions: 0, reach: 0, saved: 0 };

  const json = await res.json();
  if (!Array.isArray(json.data)) return { impressions: 0, reach: 0, saved: 0 };

  const out = { impressions: 0, reach: 0, saved: 0 };
  for (const m of json.data) {
    if (m.name === "impressions") out.impressions = m.values?.[0]?.value ?? m.value ?? 0;
    if (m.name === "reach") out.reach = m.values?.[0]?.value ?? m.value ?? 0;
    if (m.name === "saved") out.saved = m.values?.[0]?.value ?? m.value ?? 0;
  }
  return out;
}

async function refreshIgPosts() {
  if (!IG_TOKEN) throw new Error("INSTAGRAM_USER_TOKEN not set");
  if (!IG_ACCOUNT_ID) throw new Error("INSTAGRAM_ACCOUNT_ID not set");

  const url = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/media`);
  url.searchParams.set(
    "fields",
    "id,caption,media_type,timestamp,permalink,like_count,comments_count",
  );
  url.searchParams.set("limit", "25");
  url.searchParams.set("access_token", IG_TOKEN);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`IG API failed: ${res.status} ${await res.text()}`);

  const json = await res.json();
  const posts = json.data ?? [];

  const upsert = db.prepare(`
    INSERT INTO instagram_posts
      (post_id, caption, media_type, timestamp, permalink, like_count, comments_count, impressions, reach, saved, fetched_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(post_id) DO UPDATE SET
      caption=excluded.caption,
      like_count=excluded.like_count,
      comments_count=excluded.comments_count,
      impressions=excluded.impressions,
      reach=excluded.reach,
      saved=excluded.saved,
      fetched_at=excluded.fetched_at
  `);

  const now = new Date().toISOString();
  for (const p of posts) {
    const insights = await fetchInsights(p.id);
    upsert.run(
      p.id,
      p.caption ?? null,
      p.media_type ?? null,
      p.timestamp,
      p.permalink ?? null,
      p.like_count ?? 0,
      p.comments_count ?? 0,
      insights.impressions,
      insights.reach,
      insights.saved,
      now,
    );
  }
  return posts.length;
}

function isStale() {
  const row = db.prepare("SELECT MAX(fetched_at) as last FROM instagram_posts").get() as { last: string | null };
  if (!row?.last) return true;
  return Date.now() - new Date(row.last).getTime() > 60 * 60 * 1000;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const forceRefresh = searchParams.get("refresh") === "1";

  if (forceRefresh || isStale()) {
    try {
      await refreshIgPosts();
    } catch (err) {
      if (forceRefresh) {
        const msg = err instanceof Error ? err.message : String(err);
        return NextResponse.json({ error: "Refresh failed", detail: msg }, { status: 500 });
      }
    }
  }

  const rows = db
    .prepare(
      `SELECT post_id, caption, media_type, timestamp, permalink,
              like_count, comments_count, impressions, reach, saved, fetched_at
       FROM instagram_posts
       ORDER BY timestamp DESC
       LIMIT 25`,
    )
    .all();

  return NextResponse.json({ posts: rows, count: rows.length });
}
