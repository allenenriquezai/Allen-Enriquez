import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

type AssetRow = {
  id: number;
  path: string;
  type: string;
  title: string | null;
  created_at: string;
};

type PostRow = {
  id: number;
  asset_id: number;
  platform: string;
  posted_at: string | null;
  url: string | null;
};

// GET /api/library — returns assets grouped by type, with posts joined
export async function GET() {
  const assets = db
    .prepare("SELECT * FROM assets ORDER BY created_at DESC, id DESC")
    .all() as AssetRow[];
  const posts = db
    .prepare("SELECT * FROM posts ORDER BY posted_at DESC")
    .all() as PostRow[];

  const postsByAsset = new Map<number, PostRow[]>();
  for (const p of posts) {
    const arr = postsByAsset.get(p.asset_id) ?? [];
    arr.push(p);
    postsByAsset.set(p.asset_id, arr);
  }

  const groups: Record<string, Array<AssetRow & { posts: PostRow[] }>> = {};
  for (const a of assets) {
    const withPosts = { ...a, posts: postsByAsset.get(a.id) ?? [] };
    if (!groups[a.type]) groups[a.type] = [];
    groups[a.type].push(withPosts);
  }
  return NextResponse.json({ groups });
}

// POST /api/library  body: { path, type, title?, url?, idea_id?, duration_seconds? }
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { path, type, title, url, idea_id, duration_seconds } = body ?? {};
  if (!path || !type) {
    return NextResponse.json({ error: "path and type required" }, { status: 400 });
  }
  const result = db
    .prepare(
      "INSERT INTO assets (path, type, title, url, idea_id, duration_seconds) VALUES (?, ?, ?, ?, ?, ?)",
    )
    .run(path, type, title ?? null, url ?? null, idea_id ?? null, duration_seconds ?? null);
  const asset = db.prepare("SELECT * FROM assets WHERE id = ?").get(result.lastInsertRowid);
  return NextResponse.json({ asset }, { status: 201 });
}

// PATCH /api/library  body: { id, title? } — also supports /api/library/[id]
export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id } = body ?? {};
  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }
  return patchAssetRow(Number(id), body);
}

export function patchAssetRow(
  id: number,
  body: Record<string, unknown>,
): NextResponse {
  const existing = db.prepare("SELECT * FROM assets WHERE id = ?").get(id);
  if (!existing) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const fields: string[] = [];
  const values: unknown[] = [];
  for (const key of ["title", "type", "url", "idea_id", "thumbnail_url", "duration_seconds"] as const) {
    if (key in body && body[key] !== undefined) {
      fields.push(`${key} = ?`);
      values.push(body[key]);
    }
  }
  if (fields.length === 0) {
    return NextResponse.json({ asset: existing });
  }
  values.push(id);
  db.prepare(`UPDATE assets SET ${fields.join(", ")} WHERE id = ?`).run(
    ...values,
  );
  const row = db.prepare("SELECT * FROM assets WHERE id = ?").get(id);
  return NextResponse.json({ asset: row });
}
