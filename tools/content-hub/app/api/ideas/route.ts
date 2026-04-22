import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/ideas?status=new&pillar=fundamental
// Returns ideas with a script_count.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");
  const pillar = searchParams.get("pillar");

  const where: string[] = [];
  const params: unknown[] = [];
  if (status && status !== "all") {
    where.push("i.status = ?");
    params.push(status);
  }
  if (pillar && pillar !== "all") {
    where.push("i.pillar = ?");
    params.push(pillar);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const rows = db
    .prepare(
      `SELECT i.*, (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count
       FROM ideas i
       ${whereSql}
       ORDER BY
         CASE i.status WHEN 'new' THEN 0 WHEN 'bookmarked' THEN 1 WHEN 'picked' THEN 2 ELSE 3 END,
         i.batch IS NULL, i.batch,
         i.slot IS NULL, i.slot,
         i.id DESC`,
    )
    .all(...params);

  return NextResponse.json({ ideas: rows });
}

// POST /api/ideas
// Two shapes:
//   1) { id, action: 'pick'|'skip'|'bookmark' } — updates status on existing idea
//   2) { title, ... }                            — creates a new idea (used by Learning "Copy to Ideation")
export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  if (typeof body.action === "string") {
    const id = body.id as number | undefined;
    const action = body.action as string;
    if (!id) {
      return NextResponse.json({ error: "id required" }, { status: 400 });
    }
    const map: Record<string, string> = {
      pick: "picked",
      skip: "dismissed",
      bookmark: "bookmarked",
    };
    const nextStatus = map[action];
    if (!nextStatus) {
      return NextResponse.json({ error: "unknown action" }, { status: 400 });
    }
    const existing = db.prepare(`SELECT id FROM ideas WHERE id = ?`).get(id) as
      | { id: number }
      | undefined;
    if (!existing) {
      return NextResponse.json({ error: "idea not found" }, { status: 404 });
    }
    db.prepare(`UPDATE ideas SET status = ? WHERE id = ?`).run(nextStatus, id);
    return NextResponse.json({ ok: true, id, status: nextStatus });
  }

  const title = typeof body.title === "string" ? body.title.trim() : "";
  if (!title) {
    return NextResponse.json(
      { error: "title required to create idea" },
      { status: 400 },
    );
  }

  const info = db
    .prepare(
      `INSERT INTO ideas (title, hook, pillar, lane, category, modeled_after, source_platform, source_url, batch, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(
      title,
      (body.hook as string) ?? null,
      (body.pillar as string) ?? "research",
      (body.lane as string) ?? null,
      (body.category as string) ?? null,
      (body.modeled_after as string) ?? null,
      (body.source_platform as string) ?? null,
      (body.source_url as string) ?? null,
      (body.batch as string) ?? "learning",
      (body.status as string) ?? "new",
    );

  return NextResponse.json(
    { ok: true, id: info.lastInsertRowid, created: true },
    { status: 201 },
  );
}
