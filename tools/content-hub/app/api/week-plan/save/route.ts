import { NextResponse } from "next/server";
import db from "@/lib/db";

type Theme = {
  day: string;
  theme: string;
  pillar?: string | null;
  notes?: string | null;
};

export async function POST(req: Request) {
  let body: { week_start?: string; themes?: Theme[] };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  if (!body.week_start || !Array.isArray(body.themes) || body.themes.length === 0) {
    return NextResponse.json({ error: "week_start + themes required" }, { status: 400 });
  }

  const upsert = db.prepare(
    `INSERT INTO week_themes (week_start, day_of_week, theme, pillar, notes)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(week_start, day_of_week) DO UPDATE SET
       theme = excluded.theme,
       pillar = excluded.pillar,
       notes = excluded.notes`,
  );

  const tx = db.transaction((themes: Theme[]) => {
    for (const t of themes) {
      if (!t.day || !t.theme) continue;
      upsert.run(body.week_start, t.day, t.theme, t.pillar ?? null, t.notes ?? null);
    }
  });

  tx(body.themes);

  const rows = db
    .prepare(
      `SELECT id, week_start, day_of_week, theme, pillar, notes, ideas_generated
       FROM week_themes WHERE week_start = ?
       ORDER BY CASE day_of_week
         WHEN 'Mon' THEN 1 WHEN 'Tue' THEN 2 WHEN 'Wed' THEN 3
         WHEN 'Thu' THEN 4 WHEN 'Fri' THEN 5 WHEN 'Sat' THEN 6 WHEN 'Sun' THEN 7
       END`,
    )
    .all(body.week_start);

  return NextResponse.json({ week_start: body.week_start, themes: rows });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const weekStart = url.searchParams.get("week_start");
  if (!weekStart) {
    return NextResponse.json({ error: "week_start required" }, { status: 400 });
  }
  const rows = db
    .prepare(
      `SELECT id, week_start, day_of_week, theme, pillar, notes, ideas_generated
       FROM week_themes WHERE week_start = ?
       ORDER BY CASE day_of_week
         WHEN 'Mon' THEN 1 WHEN 'Tue' THEN 2 WHEN 'Wed' THEN 3
         WHEN 'Thu' THEN 4 WHEN 'Fri' THEN 5 WHEN 'Sat' THEN 6 WHEN 'Sun' THEN 7
       END`,
    )
    .all(weekStart);
  return NextResponse.json({ week_start: weekStart, themes: rows });
}

export async function DELETE(req: Request) {
  const url = new URL(req.url);
  const weekStart = url.searchParams.get("week_start");
  if (!weekStart) {
    return NextResponse.json({ error: "week_start required" }, { status: 400 });
  }
  db.prepare("DELETE FROM week_themes WHERE week_start = ?").run(weekStart);
  return NextResponse.json({ ok: true });
}
