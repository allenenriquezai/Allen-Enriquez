import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

type ScheduleRow = {
  id: number;
  script_id: number | null;
  slot_date: string;
  slot_type: string;
  pillar: string | null;
  status: string;
  notes: string | null;
  script_body: string | null;
  idea_title: string | null;
};

// GET /api/schedule?year=2026&month=4
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const yearStr = searchParams.get("year");
  const monthStr = searchParams.get("month");
  if (!yearStr || !monthStr) {
    return NextResponse.json(
      { error: "year and month required" },
      { status: 400 },
    );
  }
  const year = parseInt(yearStr, 10);
  const month = parseInt(monthStr, 10);
  if (!Number.isFinite(year) || !Number.isFinite(month)) {
    return NextResponse.json({ error: "invalid year/month" }, { status: 400 });
  }

  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  // Exclusive upper bound = first of next month
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const end = `${nextYear}-${String(nextMonth).padStart(2, "0")}-01`;

  const rows = db
    .prepare(
      `SELECT s.id, s.script_id, s.slot_date, s.slot_type, s.pillar, s.status, s.notes,
              sc.body AS script_body,
              i.title AS idea_title
       FROM schedule s
       LEFT JOIN scripts sc ON sc.id = s.script_id
       LEFT JOIN ideas i ON i.id = sc.idea_id
       WHERE s.slot_date >= ? AND s.slot_date < ?
       ORDER BY s.slot_date ASC, s.slot_type ASC`,
    )
    .all(start, end) as ScheduleRow[];

  return NextResponse.json({ slots: rows });
}

// POST /api/schedule  body: { script_id?, slot_date, slot_type, pillar?, status?, notes? }
export async function POST(req: NextRequest) {
  const body = await req.json();
  const {
    script_id = null,
    slot_date,
    slot_type,
    pillar = null,
    status = "planned",
    notes = null,
  } = body ?? {};
  if (!slot_date || !slot_type) {
    return NextResponse.json(
      { error: "slot_date and slot_type required" },
      { status: 400 },
    );
  }
  const info = db
    .prepare(
      `INSERT INTO schedule (script_id, slot_date, slot_type, pillar, status, notes)
       VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .run(script_id, slot_date, slot_type, pillar, status, notes);
  const row = db
    .prepare("SELECT * FROM schedule WHERE id = ?")
    .get(info.lastInsertRowid);
  return NextResponse.json({ slot: row }, { status: 201 });
}

// PATCH /api/schedule  body: { id, slot_date?, status?, script_id?, notes?, pillar? }
// (also supports /api/schedule/[id] via the dynamic route file)
export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id } = body ?? {};
  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }
  return patchScheduleRow(Number(id), body);
}

export function patchScheduleRow(
  id: number,
  body: Record<string, unknown>,
): NextResponse {
  const existing = db.prepare("SELECT * FROM schedule WHERE id = ?").get(id);
  if (!existing) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const fields: string[] = [];
  const values: unknown[] = [];
  for (const key of [
    "slot_date",
    "slot_type",
    "status",
    "script_id",
    "asset_id",
    "notes",
    "pillar",
  ] as const) {
    if (key in body && body[key] !== undefined) {
      fields.push(`${key} = ?`);
      values.push(body[key]);
    }
  }
  if (fields.length === 0) {
    return NextResponse.json({ slot: existing });
  }
  values.push(id);
  db.prepare(`UPDATE schedule SET ${fields.join(", ")} WHERE id = ?`).run(
    ...values,
  );
  const row = db.prepare("SELECT * FROM schedule WHERE id = ?").get(id);
  return NextResponse.json({ slot: row });
}
