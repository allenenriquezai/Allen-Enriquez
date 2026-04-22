import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/metrics?post_id=X&platform=Y
// If post_id: returns metrics for that post_id.
// If platform: joins posts and filters by platform. Includes asset title for convenience.
// Default: returns all metrics joined with posts+assets, sorted by recorded_at desc.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const postId = searchParams.get("post_id");
  const platform = searchParams.get("platform");

  const where: string[] = [];
  const params: unknown[] = [];
  if (postId) {
    where.push("m.post_id = ?");
    params.push(Number(postId));
  }
  if (platform && platform !== "all") {
    where.push("p.platform = ?");
    params.push(platform);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const rows = db
    .prepare(
      `SELECT m.*, p.platform, p.url AS post_url, p.posted_at, a.title AS asset_title, a.type AS asset_type
       FROM metrics m
       LEFT JOIN posts p ON p.id = m.post_id
       LEFT JOIN assets a ON a.id = p.asset_id
       ${whereSql}
       ORDER BY datetime(m.recorded_at) DESC, m.id DESC`,
    )
    .all(...params);

  return NextResponse.json({ metrics: rows });
}

// POST /api/metrics
// Body: { post_id, views, likes, comments, shares, saves, follows_gained, recorded_at }
export async function POST(req: Request) {
  let body: {
    post_id?: number;
    views?: number;
    likes?: number;
    comments?: number;
    shares?: number;
    saves?: number;
    follows_gained?: number;
    recorded_at?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  if (!body.post_id) {
    return NextResponse.json({ error: "post_id required" }, { status: 400 });
  }
  const info = db
    .prepare(
      `INSERT INTO metrics (post_id, views, likes, comments, shares, saves, follows_gained, recorded_at)
       VALUES (@post_id, @views, @likes, @comments, @shares, @saves, @follows_gained, COALESCE(@recorded_at, CURRENT_TIMESTAMP))`,
    )
    .run({
      post_id: body.post_id,
      views: body.views ?? 0,
      likes: body.likes ?? 0,
      comments: body.comments ?? 0,
      shares: body.shares ?? 0,
      saves: body.saves ?? 0,
      follows_gained: body.follows_gained ?? 0,
      recorded_at: body.recorded_at ?? null,
    });
  const row = db
    .prepare(`SELECT * FROM metrics WHERE id = ?`)
    .get(Number(info.lastInsertRowid));
  return NextResponse.json({ ok: true, metric: row });
}
