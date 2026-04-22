import { NextResponse } from "next/server";
import db from "@/lib/db";

// PATCH /api/inbox/:id  — update reply_text, status, thread_text
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const rowId = Number(id);
  if (!rowId) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
  let body: { reply_text?: string; status?: string; thread_text?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const existing = db
    .prepare(`SELECT * FROM inbox WHERE id = ?`)
    .get(rowId) as { id: number } | undefined;
  if (!existing) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const fields: string[] = [];
  const args: unknown[] = [];
  if (body.reply_text !== undefined) {
    fields.push("reply_text = ?");
    args.push(body.reply_text);
  }
  if (body.status !== undefined) {
    fields.push("status = ?");
    args.push(body.status);
  }
  if (body.thread_text !== undefined) {
    fields.push("thread_text = ?");
    args.push(body.thread_text);
  }
  if (!fields.length) {
    return NextResponse.json({ error: "nothing to update" }, { status: 400 });
  }
  args.push(rowId);
  db.prepare(`UPDATE inbox SET ${fields.join(", ")} WHERE id = ?`).run(...args);
  const row = db.prepare(`SELECT * FROM inbox WHERE id = ?`).get(rowId);
  return NextResponse.json({ ok: true, message: row });
}
