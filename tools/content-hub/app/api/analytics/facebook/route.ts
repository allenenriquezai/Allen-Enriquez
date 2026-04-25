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

async function fetchPostInsights(postId: string): Promise<{ reach: number; impressions: number }> {
  try {
    const url = new URL(`${FB_BASE}/${postId}/insights`);
    url.searchParams.set("metric", "post_video_views,post_video_views_unique");
    url.searchParams.set("access_token", PAGE_TOKEN);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return { reach: 0, impressions: 0 };
    const json = await res.json();
    const metrics: Record<string, number> = {};
    for (const m of json.data ?? []) {
      if (m.period === "lifetime") {
        metrics[m.name] = m.values?.[0]?.value ?? 0;
      }
    }
    return {
      reach: metrics.post_video_views ?? 0,
      impressions: metrics.post_video_views_unique ?? 0,
    };
  } catch {
    return { reach: 0, impressions: 0 };
  }
}

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

  const insightsResults = await Promise.all(
    posts.map((p: Record<string, unknown>) => fetchPostInsights(p.id as string).then(ins => ({ id: p.id as string, ...ins })))
  );
  const insightsMap = new Map(insightsResults.map(r => [r.id, r]));

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
    const ins = insightsMap.get(p.id as string) ?? { reach: 0, impressions: 0 };
    const reactions = (p.reactions as { summary?: { total_count?: number } })?.summary?.total_count ?? 0;
    const comments = (p.comments as { summary?: { total_count?: number } })?.summary?.total_count ?? 0;
    const shares = (p.shares as { count?: number })?.count ?? 0;
    upsert.run(
      p.id,
      (p.message ?? p.story ?? null) as string | null,
      p.created_time,
      (p.permalink_url ?? null) as string | null,
      ins.impressions,
      ins.reach,
      reactions + comments + shares,
      reactions,
      comments,
      shares,
      now,
    );
  }
  return posts.length;
}

function isStale() {
  const row = db.prepare("SELECT MAX(fetched_at) as last FROM facebook_posts").get() as { last: string | null };
  if (!row?.last) return true;
  return Date.now() - new Date(row.last).getTime() > 60 * 60 * 1000;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const forceRefresh = searchParams.get("refresh") === "1";

  if (forceRefresh || isStale()) {
    try {
      await refreshFbPosts();
    } catch (err) {
      if (forceRefresh) {
        const msg = err instanceof Error ? err.message : String(err);
        return NextResponse.json({ error: "Refresh failed", detail: msg }, { status: 500 });
      }
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
