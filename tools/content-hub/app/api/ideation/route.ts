import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const tag = searchParams.get("tag");
  const author = searchParams.get("author");

  let sql = "SELECT * FROM ideation_notes WHERE 1=1";
  const params: (string | number)[] = [];
  if (tag) {
    sql += " AND tags LIKE ?";
    params.push(`%${tag}%`);
  }
  if (author) {
    sql += " AND author = ?";
    params.push(author);
  }
  sql += " ORDER BY pinned DESC, updated_at DESC";
  const notes = db.prepare(sql).all(...params);
  return NextResponse.json({ notes });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { title, body: noteBody, tags, author, pinned } = body;
  if (!title) {
    return NextResponse.json({ error: "title required" }, { status: 400 });
  }
  const info = db
    .prepare(
      "INSERT INTO ideation_notes (title, body, tags, author, pinned) VALUES (?, ?, ?, ?, ?)",
    )
    .run(title, noteBody ?? "", tags ?? "", author ?? "allen", pinned ? 1 : 0);
  const note = db
    .prepare("SELECT * FROM ideation_notes WHERE id = ?")
    .get(info.lastInsertRowid);
  return NextResponse.json({ note });
}
