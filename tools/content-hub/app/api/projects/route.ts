import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/projects — list all projects with computed status from v_project_status,
// plus child counts (scripts, assets, posts) and source link metadata.
// Optional ?status=ready,scripted to filter; ?include_archived=1 includes archived.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const statusFilter = searchParams.get("status");
  const includeArchived = searchParams.get("include_archived") === "1";

  type Row = {
    id: number;
    title: string;
    hook: string | null;
    pillar: string | null;
    archived: number;
    source_type: string | null;
    source_ref_table: string | null;
    source_ref_id: number | null;
    source_url: string | null;
    modeled_after: string | null;
    created_at: string;
    notes: string | null;
    computed_status: string;
    script_count: number;
    asset_count: number;
    post_count: number;
    latest_thumbnail: string | null;
  };

  const rows = db
    .prepare(
      `
      SELECT i.id, i.title, i.hook, i.pillar, i.archived, i.source_type,
             i.source_ref_table, i.source_ref_id, i.source_url, i.modeled_after,
             i.created_at, i.notes,
             v.status AS computed_status,
             (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count,
             (SELECT COUNT(*) FROM assets a WHERE a.idea_id = i.id) AS asset_count,
             (SELECT COUNT(*) FROM posts po
                JOIN assets a2 ON po.asset_id = a2.id
                WHERE a2.idea_id = i.id) AS post_count,
             (SELECT a3.url FROM assets a3
                WHERE a3.idea_id = i.id AND a3.url IS NOT NULL
                ORDER BY a3.created_at DESC LIMIT 1) AS latest_thumbnail
      FROM ideas i
      LEFT JOIN v_project_status v ON v.project_id = i.id
      ORDER BY i.created_at DESC, i.id DESC
      `,
    )
    .all() as Row[];

  let filtered = rows;
  if (!includeArchived) filtered = filtered.filter((r) => r.archived !== 1);
  if (statusFilter) {
    const want = new Set(statusFilter.split(",").map((s) => s.trim()));
    filtered = filtered.filter((r) => want.has(r.computed_status));
  }

  // Group by computed status (Kanban columns)
  const columns: Record<string, Row[]> = {
    draft: [],
    scripted: [],
    filming: [],
    editing: [],
    ready: [],
    scheduled: [],
    posted: [],
    archived: [],
  };
  for (const r of filtered) {
    const col = columns[r.computed_status];
    if (col) col.push(r);
  }
  return NextResponse.json({ projects: filtered, columns });
}
