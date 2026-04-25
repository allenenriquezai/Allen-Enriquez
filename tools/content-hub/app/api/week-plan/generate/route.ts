import { NextResponse } from "next/server";
import db from "@/lib/db";

// Calls /api/ideas/generate internally for the requested day(s) of a saved week.
// Marks week_themes.ideas_generated=1 when done.

type ThemeRow = {
  id: number;
  week_start: string;
  day_of_week: string;
  theme: string;
  pillar: string | null;
};

export async function POST(req: Request) {
  let body: { week_start?: string; day_of_week?: string; count?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  if (!body.week_start) {
    return NextResponse.json({ error: "week_start required" }, { status: 400 });
  }
  const count = Math.min(Math.max(1, body.count ?? 10), 20);

  let themes: ThemeRow[];
  if (body.day_of_week) {
    themes = db
      .prepare(
        `SELECT id, week_start, day_of_week, theme, pillar
         FROM week_themes WHERE week_start = ? AND day_of_week = ?`,
      )
      .all(body.week_start, body.day_of_week) as ThemeRow[];
  } else {
    themes = db
      .prepare(
        `SELECT id, week_start, day_of_week, theme, pillar
         FROM week_themes WHERE week_start = ? AND ideas_generated = 0`,
      )
      .all(body.week_start) as ThemeRow[];
  }

  if (themes.length === 0) {
    return NextResponse.json({ generated: [], message: "No themes to generate" });
  }

  const origin = new URL(req.url).origin;
  const markDone = db.prepare(
    `UPDATE week_themes SET ideas_generated = 1 WHERE id = ?`,
  );

  const generated: Array<{ day: string; theme: string; ideas_count: number }> = [];

  for (const t of themes) {
    try {
      const res = await fetch(`${origin}/api/ideas/generate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          count,
          day_of_week: t.day_of_week,
          theme: t.theme,
          pillar: t.pillar,
          batch: `week_${t.week_start}`,
        }),
      });
      const json = await res.json();
      const n = Array.isArray(json.ideas) ? json.ideas.length : 0;
      if (n > 0) markDone.run(t.id);
      generated.push({ day: t.day_of_week, theme: t.theme, ideas_count: n });
    } catch (err) {
      console.error(`[week-plan/generate] failed ${t.day_of_week}:`, err);
      generated.push({ day: t.day_of_week, theme: t.theme, ideas_count: 0 });
    }
  }

  return NextResponse.json({ week_start: body.week_start, generated });
}
