import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

// POST /api/projects/from-note  body: { note_id: number, pillar?: string }
// Promotes an ideation_notes row to a project (ideas row), keeps note linked back.
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const noteId = Number(body.note_id);
  if (!Number.isFinite(noteId)) {
    return NextResponse.json({ error: "valid note_id required" }, { status: 400 });
  }

  const note = db
    .prepare("SELECT id, title, body, tags, idea_id FROM ideation_notes WHERE id = ?")
    .get(noteId) as
    | { id: number; title: string; body: string | null; tags: string | null; idea_id: number | null }
    | undefined;
  if (!note) return NextResponse.json({ error: "note not found" }, { status: 404 });
  if (note.idea_id) {
    return NextResponse.json({ error: "note already linked to project", project_id: note.idea_id }, { status: 409 });
  }

  const result = db
    .prepare(
      `INSERT INTO ideas
        (title, hook, pillar, status, source_type, batch, notes)
       VALUES (?, ?, ?, 'picked', 'raw', 'notes', ?)`,
    )
    .run(
      note.title,
      note.body?.slice(0, 200) ?? null,
      (body.pillar as string) ?? "research",
      note.body ?? null,
    );

  const projectId = Number(result.lastInsertRowid);
  db.prepare("UPDATE ideation_notes SET idea_id = ? WHERE id = ?").run(projectId, noteId);

  return NextResponse.json({ ok: true, id: projectId, note_id: noteId, created: true }, { status: 201 });
}
