import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

const TT_BASE = "https://open.tiktokapis.com/v2";

function readCached() {
  return db
    .prepare(
      "SELECT video_id, title, view_count, like_count, comment_count, share_count, published_at, updated_at FROM tiktok_stats ORDER BY published_at DESC LIMIT 50",
    )
    .all();
}

function isStale() {
  const row = db.prepare("SELECT MAX(updated_at) as last FROM tiktok_stats").get() as { last: string | null };
  if (!row?.last) return true;
  return Date.now() - new Date(row.last).getTime() > 60 * 60 * 1000;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const forceRefresh = searchParams.get("refresh") === "1";

  if (!forceRefresh && !isStale()) {
    return NextResponse.json({ stats: readCached() });
  }

  let token: string;
  try {
    token = await getToken("tiktok");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: msg, stats: readCached() },
      { status: forceRefresh ? 401 : 200 },
    );
  }

  const res = await fetch(`${TT_BASE}/video/list/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
    },
    body: JSON.stringify({
      max_count: 20,
      fields: ["id", "title", "create_time", "view_count", "like_count", "comment_count", "share_count"],
    }),
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: "TikTok API failed", detail: await res.text(), stats: readCached() },
      { status: 500 },
    );
  }

  const json = await res.json();
  const videos = json.data?.videos ?? [];

  const upsert = db.prepare(`
    INSERT INTO tiktok_stats (video_id, title, view_count, like_count, comment_count, share_count, published_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(video_id) DO UPDATE SET
      title = excluded.title,
      view_count = excluded.view_count,
      like_count = excluded.like_count,
      comment_count = excluded.comment_count,
      share_count = excluded.share_count,
      updated_at = excluded.updated_at
  `);

  const now = new Date().toISOString();
  for (const v of videos) {
    upsert.run(
      String(v.id),
      v.title ?? null,
      v.view_count ?? 0,
      v.like_count ?? 0,
      v.comment_count ?? 0,
      v.share_count ?? 0,
      v.create_time ? new Date(v.create_time * 1000).toISOString() : null,
      now,
    );
  }

  return NextResponse.json({ videos, count: videos.length, stats: readCached() });
}
