import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/learning?category=X
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const category = searchParams.get("category");
  const where: string[] = [];
  const params: unknown[] = [];
  if (category && category !== "all") {
    where.push("category = ?");
    params.push(category);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const rows = db
    .prepare(
      `SELECT * FROM learning_refs ${whereSql} ORDER BY datetime(saved_at) DESC, id DESC`,
    )
    .all(...params);
  return NextResponse.json({ refs: rows });
}

// POST /api/learning
export async function POST(req: Request) {
  let body: {
    url?: string;
    creator?: string;
    platform?: string;
    category?: string;
    title?: string;
    notes?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const info = db
    .prepare(
      `INSERT INTO learning_refs (url, creator, platform, category, title, notes)
       VALUES (@url, @creator, @platform, @category, @title, @notes)`,
    )
    .run({
      url: body.url ?? null,
      creator: body.creator ?? null,
      platform: body.platform ?? null,
      category: body.category ?? "viral_ref",
      title: body.title ?? null,
      notes: body.notes ?? null,
    });
  const row = db
    .prepare(`SELECT * FROM learning_refs WHERE id = ?`)
    .get(Number(info.lastInsertRowid));
  return NextResponse.json({ ok: true, ref: row });
}
