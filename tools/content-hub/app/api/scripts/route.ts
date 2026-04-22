import { NextResponse } from "next/server";
import db from "@/lib/db";
import { countWords } from "@/lib/importers/drafts";

// GET /api/scripts?idea_id=123 — returns all scripts for an idea.
// GET /api/scripts — returns all scripts grouped by idea.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const ideaIdRaw = searchParams.get("idea_id");

  if (ideaIdRaw) {
    const ideaId = Number(ideaIdRaw);
    if (!Number.isFinite(ideaId)) {
      return NextResponse.json({ error: "invalid idea_id" }, { status: 400 });
    }
    const idea = db.prepare(`SELECT * FROM ideas WHERE id = ?`).get(ideaId);
    const scripts = db
      .prepare(`SELECT * FROM scripts WHERE idea_id = ? ORDER BY variant`)
      .all(ideaId);
    return NextResponse.json({ idea, scripts });
  }

  const scripts = db
    .prepare(
      `SELECT s.*, i.title AS idea_title, i.pillar AS idea_pillar, i.status AS idea_status
       FROM scripts s JOIN ideas i ON i.id = s.idea_id
       ORDER BY i.id DESC, s.variant`,
    )
    .all();
  return NextResponse.json({ scripts });
}

// POST /api/scripts  { idea_id, variant, body? }
// Creates an empty script row (used when user opens a variant tab that doesn't
// exist yet and hits Save). Idempotent — returns existing row if one exists.
export async function POST(req: Request) {
  let body: { idea_id?: number; variant?: string; body?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const { idea_id, variant } = body;
  const text = body.body ?? "";
  if (!idea_id || !variant) {
    return NextResponse.json(
      { error: "idea_id and variant required" },
      { status: 400 },
    );
  }

  const existing = db
    .prepare(`SELECT * FROM scripts WHERE idea_id = ? AND variant = ?`)
    .get(idea_id, variant) as { id: number } | undefined;

  if (existing) {
    if (text) {
      db.prepare(
        `UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
      ).run(text, countWords(text), existing.id);
    }
    return NextResponse.json({ id: existing.id, created: false });
  }

  const info = db
    .prepare(
      `INSERT INTO scripts (idea_id, variant, body, word_count, updated_at)
       VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
    )
    .run(idea_id, variant, text, countWords(text));
  return NextResponse.json({ id: Number(info.lastInsertRowid), created: true });
}
