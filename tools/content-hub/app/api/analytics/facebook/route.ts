import { NextResponse } from "next/server";
import db from "@/lib/db";

const PAGE_ID = process.env.FACEBOOK_PAGE_ID!;
const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;
const FB_BASE = "https://graph.facebook.com/v25.0";

db.exec(`
  CREATE TABLE IF NOT EXISTS facebook_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL UNIQUE,
    message TEXT,
    created_time TEXT,
    permalink_url TEXT,
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engaged_users INTEGER DEFAULT 0,
    reactions INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX IF NOT EXISTS idx_fb_posts_created ON facebook_posts(created_time DESC);
`);

async function refreshFbPosts() {
  if (!PAGE_TOKEN) throw new Error("FACEBOOK_PAGE_ACCESS_TOKEN not set");

  const fields = [
    "id",
    "message",
    "story",
    "created_time",
    "permalink_url",
    "reactions.summary(true)",
    "comments.summary(true)",
    "shares",
  ].join(",");

  const url = new URL(`${FB_BASE}/${PAGE_ID}/posts`);
  url.searchParams.set("fields", fields);
  url.searchParams.set("limit", "25");
  url.searchParams.set("access_token", PAGE_TOKEN);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`FB API failed: ${res.status} ${await res.text()}`);

  const json = await res.json();
  const posts = json.data ?? [];

  const upsert = db.prepare(`
    INSERT INTO facebook_posts
      (post_id, message, created_time, permalink_url, impressions, reach, engaged_users, reactions, comments_count, shares_count, fetched_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(post_id) DO UPDATE SET
      message=excluded.message,
      impressions=excluded.impressions,
      reach=excluded.reach,
      engaged_users=excluded.engaged_users,
      reactions=excluded.reactions,
      comments_count=excluded.comments_count,
      shares_count=excluded.shares_count,
      fetched_at=excluded.fetched_at
  `);

  const now = new Date().toISOString();
  for (const p of posts) {
    let impressions = 0, reach = 0, engagedUsers = 0;
    if (Array.isArray(p.insights?.data)) {
      for (const metric of p.insights.data) {
        const val = metric.values?.[0]?.value ?? 0;
        if (metric.name === "post_impressions") impressions = val;
        if (metric.name === "post_impressions_unique") reach = val;
        if (metric.name === "post_engaged_users") engagedUsers = val;
      }
    }
    upsert.run(
      p.id,
      p.message ?? p.story ?? null,
      p.created_time,
      p.permalink_url ?? null,
      impressions,
      reach,
      engagedUsers,
      p.reactions?.summary?.total_count ?? 0,
      p.comments?.summary?.total_count ?? 0,
      p.shares?.count ?? 0,
      now,
    );
  }
  return posts.length;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);

  if (searchParams.get("refresh") === "1") {
    try {
      await refreshFbPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return NextResponse.json({ error: "Refresh failed", detail: msg }, { status: 500 });
    }
  }

  const rows = db
    .prepare(
      `SELECT post_id, message, created_time, permalink_url,
              impressions, reach, engaged_users, reactions, comments_count, shares_count, fetched_at
       FROM facebook_posts
       ORDER BY created_time DESC
       LIMIT 25`,
    )
    .all();

  return NextResponse.json({ posts: rows, count: rows.length });
}
