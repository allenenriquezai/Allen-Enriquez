import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

export async function GET() {
  const tags = db
    .prepare("SELECT id, name FROM ideation_tags ORDER BY name ASC")
    .all() as { id: number; name: string }[];
  return NextResponse.json({ tags });
}

export async function POST(req: NextRequest) {
  let body: { name?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const name = body.name?.trim().toLowerCase();
  if (!name) {
    return NextResponse.json({ error: "name required" }, { status: 400 });
  }
  try {
    db.prepare("INSERT INTO ideation_tags (name) VALUES (?)").run(name);
  } catch {
    // already exists — ignore
  }
  const tag = db
    .prepare("SELECT id, name FROM ideation_tags WHERE name = ?")
    .get(name) as { id: number; name: string } | undefined;
  return NextResponse.json({ tag });
}

export async function DELETE(req: NextRequest) {
  const url = new URL(req.url);
  const id = url.searchParams.get("id");
  const name = url.searchParams.get("name");
  if (!id && !name) {
    return NextResponse.json({ error: "id or name required" }, { status: 400 });
  }
  if (id) {
    db.prepare("DELETE FROM ideation_tags WHERE id = ?").run(id);
  } else if (name) {
    db.prepare("DELETE FROM ideation_tags WHERE name = ?").run(name);
  }
  return NextResponse.json({ ok: true });
}
