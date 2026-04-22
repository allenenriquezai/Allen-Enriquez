import { NextResponse } from "next/server";
import db from "@/lib/db";
import { countWords } from "@/lib/importers/drafts";

// Next 16: params is a Promise in route handlers.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const scriptId = Number(id);
  if (!Number.isFinite(scriptId)) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
  const row = db.prepare(`SELECT * FROM scripts WHERE id = ?`).get(scriptId);
  if (!row) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  return NextResponse.json({ script: row });
}

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const scriptId = Number(id);
  if (!Number.isFinite(scriptId)) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }

  let body: { body?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const text = body.body;
  if (typeof text !== "string") {
    return NextResponse.json({ error: "body required" }, { status: 400 });
  }

  const existing = db
    .prepare(`SELECT id FROM scripts WHERE id = ?`)
    .get(scriptId);
  if (!existing) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  db.prepare(
    `UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
  ).run(text, countWords(text), scriptId);

  return NextResponse.json({ ok: true, id: scriptId, word_count: countWords(text) });
}
