import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/posts — list of posts joined with asset metadata (for metrics entry).
export async function GET() {
  const rows = db
    .prepare(
      `SELECT p.*, a.title AS asset_title, a.type AS asset_type, a.path AS asset_path
       FROM posts p
       LEFT JOIN assets a ON a.id = p.asset_id
       ORDER BY datetime(p.posted_at) DESC, p.id DESC`,
    )
    .all();
  return NextResponse.json({ posts: rows });
}

// POST /api/posts  body: { asset_id, platform, url?, status?, error_detail? }
// Logs every publish attempt — success or failure. If a previous attempt for
// the same (asset_id, platform) exists, increments attempts on the new row.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { asset_id, platform, url = null, status = "success", error_detail = null } = body ?? {};
  if (!asset_id || !platform) {
    return NextResponse.json(
      { error: "asset_id and platform required" },
      { status: 400 },
    );
  }
  const posted_at = new Date().toISOString();
  const prior = db
    .prepare(
      `SELECT COUNT(*) AS n FROM posts WHERE asset_id = ? AND platform = ?`,
    )
    .get(asset_id, platform) as { n: number };
  const attempts = (prior?.n ?? 0) + 1;
  const info = db
    .prepare(
      `INSERT INTO posts (asset_id, platform, posted_at, url, status, error_detail, attempts)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(asset_id, platform, posted_at, url, status, error_detail, attempts);
  const row = db
    .prepare("SELECT * FROM posts WHERE id = ?")
    .get(info.lastInsertRowid);
  return NextResponse.json({ post: row }, { status: 201 });
}

// DELETE /api/posts?asset_id=X&platform=Y — deletes most recent match
export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const asset_id = searchParams.get("asset_id");
  const platform = searchParams.get("platform");
  if (!asset_id || !platform) {
    return NextResponse.json(
      { error: "asset_id and platform required" },
      { status: 400 },
    );
  }
  const row = db
    .prepare(
      `SELECT id FROM posts
       WHERE asset_id = ? AND platform = ?
       ORDER BY posted_at DESC, id DESC
       LIMIT 1`,
    )
    .get(Number(asset_id), platform) as { id: number } | undefined;
  if (!row) {
    return NextResponse.json({ deleted: 0 });
  }
  db.prepare("DELETE FROM posts WHERE id = ?").run(row.id);
  return NextResponse.json({ deleted: 1, id: row.id });
}
