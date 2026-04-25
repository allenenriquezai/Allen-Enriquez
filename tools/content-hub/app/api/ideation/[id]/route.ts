import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json();
  const fields: string[] = [];
  const values: (string | number)[] = [];

  for (const key of ["title", "body", "tags", "author", "pinned"] as const) {
    if (key in body) {
      fields.push(`${key} = ?`);
      values.push(key === "pinned" ? (body[key] ? 1 : 0) : body[key]);
    }
  }
  if (fields.length === 0) {
    return NextResponse.json({ error: "no fields" }, { status: 400 });
  }
  fields.push("updated_at = CURRENT_TIMESTAMP");
  values.push(Number(id));

  db.prepare(`UPDATE ideation_notes SET ${fields.join(", ")} WHERE id = ?`).run(
    ...values,
  );
  const note = db
    .prepare("SELECT * FROM ideation_notes WHERE id = ?")
    .get(Number(id));
  return NextResponse.json({ note });
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  db.prepare("DELETE FROM ideation_notes WHERE id = ?").run(Number(id));
  return NextResponse.json({ ok: true });
}
