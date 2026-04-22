import { NextResponse } from "next/server";
import db from "@/lib/db";

// PATCH /api/learning/:id
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const rowId = Number(id);
  if (!rowId) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
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
  const existing = db
    .prepare(`SELECT id FROM learning_refs WHERE id = ?`)
    .get(rowId) as { id: number } | undefined;
  if (!existing) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const fields: string[] = [];
  const args: unknown[] = [];
  for (const key of ["url", "creator", "platform", "category", "title", "notes"] as const) {
    if (body[key] !== undefined) {
      fields.push(`${key} = ?`);
      args.push(body[key]);
    }
  }
  if (!fields.length) {
    return NextResponse.json({ error: "nothing to update" }, { status: 400 });
  }
  args.push(rowId);
  db.prepare(`UPDATE learning_refs SET ${fields.join(", ")} WHERE id = ?`).run(...args);
  const row = db.prepare(`SELECT * FROM learning_refs WHERE id = ?`).get(rowId);
  return NextResponse.json({ ok: true, ref: row });
}

// DELETE /api/learning/:id
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const rowId = Number(id);
  if (!rowId) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
  const info = db.prepare(`DELETE FROM learning_refs WHERE id = ?`).run(rowId);
  if (info.changes === 0) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  return NextResponse.json({ ok: true });
}
