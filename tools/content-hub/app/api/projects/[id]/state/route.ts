import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

// POST /api/projects/[id]/state  body: { phase: 'filming' | 'editing' }
// Lets the user (Kanban card "Mark filming/editing") or a skill nudge a project
// into an interim stage when no real asset exists yet. Inserts a stub assets row
// with status=phase and idea_id=projectId so v_project_status flips.
const VALID_PHASES = new Set(["filming", "editing"]);
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const projectId = Number(id);
  if (!Number.isFinite(projectId)) {
    return NextResponse.json({ error: "invalid project id" }, { status: 400 });
  }
  const body = (await req.json().catch(() => ({}))) as { phase?: string };
  const phase = body.phase;
  if (!phase || !VALID_PHASES.has(phase)) {
    return NextResponse.json(
      { error: "phase must be 'filming' or 'editing'" },
      { status: 400 },
    );
  }

  const project = db.prepare("SELECT id FROM ideas WHERE id = ?").get(projectId) as
    | { id: number }
    | undefined;
  if (!project) return NextResponse.json({ error: "project not found" }, { status: 404 });

  // Reuse an existing stub if one exists for this project + phase
  const existing = db
    .prepare(
      "SELECT id FROM assets WHERE idea_id = ? AND status = ? AND path LIKE 'stub:%'",
    )
    .get(projectId, phase) as { id: number } | undefined;
  if (existing) {
    return NextResponse.json({ ok: true, asset_id: existing.id, reused: true });
  }

  // Walk back any newer stub that's now stale (e.g. ready already exists)
  const result = db
    .prepare(
      `INSERT INTO assets (path, type, title, idea_id, status)
       VALUES (?, 'reel', ?, ?, ?)`,
    )
    .run(
      `stub:${projectId}:${phase}:${Date.now()}`,
      `[${phase}] project ${projectId}`,
      projectId,
      phase,
    );

  const status = (db
    .prepare("SELECT status FROM v_project_status WHERE project_id = ?")
    .get(projectId) as { status: string } | undefined)?.status;

  return NextResponse.json({
    ok: true,
    asset_id: Number(result.lastInsertRowid),
    project_status: status,
  });
}
