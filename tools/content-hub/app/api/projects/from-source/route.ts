import { NextRequest, NextResponse } from "next/server";
import db from "@/lib/db";

// POST /api/projects/from-source
// body: { source_table: 'creator_posts' | 'learning_refs', source_id: number,
//         title?: string, hook?: string, pillar?: string }
// Creates a project (ideas row) linked back to the source row.
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const sourceTable = body.source_table as string | undefined;
  const sourceId = Number(body.source_id);

  if (sourceTable !== "creator_posts" && sourceTable !== "learning_refs") {
    return NextResponse.json(
      { error: "source_table must be creator_posts or learning_refs" },
      { status: 400 },
    );
  }
  if (!Number.isFinite(sourceId)) {
    return NextResponse.json({ error: "valid source_id required" }, { status: 400 });
  }

  let title: string | null = body.title ?? null;
  let hook: string | null = body.hook ?? null;
  let sourceUrl: string | null = null;
  let modeledAfter: string | null = null;
  let sourcePlatform: string | null = null;
  let sourceType = "raw";

  if (sourceTable === "creator_posts") {
    const row = db
      .prepare(
        "SELECT title, description, hook, url, creator, platform FROM creator_posts WHERE id = ?",
      )
      .get(sourceId) as
      | { title: string | null; description: string | null; hook: string | null; url: string; creator: string; platform: string }
      | undefined;
    if (!row) return NextResponse.json({ error: "creator_posts row not found" }, { status: 404 });
    title = title ?? row.title ?? row.description?.slice(0, 80) ?? "Untitled (from creator post)";
    hook = hook ?? row.hook ?? null;
    sourceUrl = row.url;
    modeledAfter = row.creator;
    sourcePlatform = row.platform;
    sourceType = "competitor_post";
  } else {
    const row = db
      .prepare(
        "SELECT title, url, creator, platform, category, notes FROM learning_refs WHERE id = ?",
      )
      .get(sourceId) as
      | { title: string | null; url: string | null; creator: string | null; platform: string | null; category: string | null; notes: string | null }
      | undefined;
    if (!row) return NextResponse.json({ error: "learning_refs row not found" }, { status: 404 });
    title = title ?? row.title ?? row.notes?.slice(0, 80) ?? "Untitled (from learning ref)";
    hook = hook ?? null;
    sourceUrl = row.url;
    modeledAfter = row.creator;
    sourcePlatform = row.platform;
    sourceType =
      row.category === "trending_topic" ? "trending"
      : row.category === "competitor_post" ? "competitor_post"
      : "viral_ref";
  }

  const result = db
    .prepare(
      `INSERT INTO ideas
        (title, hook, pillar, modeled_after, source_platform, source_url,
         status, source_type, source_ref_table, source_ref_id, batch)
       VALUES (?, ?, ?, ?, ?, ?, 'picked', ?, ?, ?, 'inspiration')`,
    )
    .run(
      title,
      hook,
      (body.pillar as string) ?? "research",
      modeledAfter,
      sourcePlatform,
      sourceUrl,
      sourceType,
      sourceTable,
      sourceId,
    );

  return NextResponse.json(
    { ok: true, id: Number(result.lastInsertRowid), created: true },
    { status: 201 },
  );
}
