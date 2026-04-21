import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/creator-feed?creator=Justyn&platform=tiktok&limit=20&offset=0
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const creator = searchParams.get("creator");
  const platform = searchParams.get("platform");
  const limit = Math.min(Number(searchParams.get("limit") || 50), 200);
  const offset = Number(searchParams.get("offset") || 0);

  const where: string[] = [];
  const params: (string | number)[] = [];
  if (creator) {
    where.push("creator = ?");
    params.push(creator);
  }
  if (platform) {
    where.push("platform = ?");
    params.push(platform);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const sql = `
    SELECT id, post_id, creator, platform, url, title, description,
           thumbnail_url, posted_at, view_count, like_count, comment_count,
           duration_sec, transcript, hook, topic, why_it_works, fetched_at
    FROM creator_posts
    ${whereSql}
    ORDER BY COALESCE(posted_at, fetched_at) DESC
    LIMIT ? OFFSET ?
  `;
  params.push(limit, offset);
  const rows = db.prepare(sql).all(...params);

  const totalRow = db
    .prepare(`SELECT COUNT(*) AS n FROM creator_posts ${whereSql}`)
    .get(...params.slice(0, params.length - 2)) as { n: number };

  return NextResponse.json({ posts: rows, total: totalRow.n });
}
