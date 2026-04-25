import { NextResponse } from "next/server";
import db from "@/lib/db";

// Next 15+: params is a Promise in route handlers.

// GET /api/ideas/[id]
// Returns a single idea row with script_count.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const ideaId = Number(id);
  if (!Number.isFinite(ideaId)) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }

  const row = db
    .prepare(
      `SELECT i.*,
              (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count
       FROM ideas i
       WHERE i.id = ?`,
    )
    .get(ideaId);

  if (!row) {
    return NextResponse.json({ error: "idea not found" }, { status: 404 });
  }

  return NextResponse.json({ idea: row });
}

// PATCH /api/ideas/[id]
// Accepts any subset of patchable fields:
//   { status, notes, title, hook, pillar, lane, category, modeled_after,
//     source_platform, source_url, day_of_week, slot, batch }
// All fields are optional; only provided keys are written.
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const ideaId = Number(id);
  if (!Number.isFinite(ideaId)) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const existing = db
    .prepare(`SELECT id FROM ideas WHERE id = ?`)
    .get(ideaId) as { id: number } | undefined;
  if (!existing) {
    return NextResponse.json({ error: "idea not found" }, { status: 404 });
  }

  const ALLOWED = [
    "status",
    "notes",
    "title",
    "hook",
    "pillar",
    "lane",
    "category",
    "modeled_after",
    "source_platform",
    "source_url",
    "day_of_week",
    "slot",
    "batch",
    "archived",
    "source_type",
    "source_ref_table",
    "source_ref_id",
    "theme",
  ] as const;

  const sets: string[] = [];
  const values: unknown[] = [];

  for (const key of ALLOWED) {
    if (Object.prototype.hasOwnProperty.call(body, key)) {
      sets.push(`${key} = ?`);
      values.push(body[key] ?? null);
    }
  }

  if (sets.length === 0) {
    return NextResponse.json(
      { error: "no patchable fields provided" },
      { status: 400 },
    );
  }

  values.push(ideaId);
  db.prepare(`UPDATE ideas SET ${sets.join(", ")} WHERE id = ?`).run(...values);

  const updated = db
    .prepare(
      `SELECT i.*,
              (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count
       FROM ideas i WHERE i.id = ?`,
    )
    .get(ideaId);

  return NextResponse.json({ ok: true, idea: updated });
}
