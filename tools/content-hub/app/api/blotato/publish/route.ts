import { NextResponse } from "next/server";
import db from "@/lib/db";
import { patchScheduleRow } from "@/app/api/schedule/route";

export async function POST(req: Request) {
  const { schedule_id } = await req.json();
  if (!schedule_id) return NextResponse.json({ error: "schedule_id required" }, { status: 400 });

  const slot = db
    .prepare(
      `SELECT sch.id, sch.slot_date, s.body AS reel_body, i.title
       FROM schedule sch
       LEFT JOIN scripts s ON s.id = sch.script_id
       LEFT JOIN ideas i ON i.id = s.idea_id
       WHERE sch.id = ?`
    )
    .get(schedule_id) as {
    id: number;
    slot_date: string;
    reel_body: string | null;
    title: string | null;
  } | undefined;

  if (!slot) return NextResponse.json({ error: "not found" }, { status: 404 });
  if (!slot.reel_body)
    return NextResponse.json({ error: "no script body — cannot publish" }, { status: 422 });

  const apiKey = process.env.BLOTATO_API_KEY;
  if (!apiKey)
    return NextResponse.json({ error: "BLOTATO_API_KEY not configured" }, { status: 500 });

  const blotatoRes = await fetch("https://backend.blotato.com/v2/posts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "blotato-api-key": apiKey,
    },
    body: JSON.stringify({
      text: slot.reel_body,
      scheduled_at: slot.slot_date,
    }),
  });

  if (!blotatoRes.ok) {
    const err = await blotatoRes.text();
    return NextResponse.json({ error: "Blotato API error", detail: err }, { status: 502 });
  }

  patchScheduleRow(schedule_id, { status: "posted" });
  return NextResponse.json({ ok: true, blotato: await blotatoRes.json() });
}
