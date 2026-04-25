import { NextRequest, NextResponse } from "next/server";
import path from "node:path";
import fs from "node:fs";
import db from "@/lib/db";
import { uploadFile } from "@/lib/r2";

type PromoteBody = {
  local_path: string;
  idea_id?: number | null;          // alias: project_id
  project_id?: number | null;
  script_id?: number | null;
  type?: string;                    // reel | youtube | carousel — default 'reel'
  title?: string;
  variant_label?: string;
  duration_seconds?: number;
  render_meta?: Record<string, unknown>;
};

function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

// POST /api/library/promote
// Uploads a locally-rendered MP4 to R2 ready/<project_id>/<asset_id>-<slug>-<file>.mp4,
// inserts an assets row with status='ready', returns { asset_id, url, key }.
export async function POST(req: NextRequest) {
  const body = (await req.json()) as PromoteBody;
  const localPath = body.local_path;
  if (!localPath) {
    return NextResponse.json({ error: "local_path required" }, { status: 400 });
  }
  if (!fs.existsSync(localPath)) {
    return NextResponse.json({ error: `file not found: ${localPath}` }, { status: 400 });
  }

  const projectId = body.project_id ?? body.idea_id ?? null;
  const scriptId = body.script_id ?? null;
  const type = body.type ?? "reel";

  let titleHint = body.title?.trim();
  if (!titleHint && projectId) {
    const idea = db
      .prepare("SELECT title FROM ideas WHERE id = ?")
      .get(projectId) as { title: string } | undefined;
    titleHint = idea?.title;
  }
  if (!titleHint) titleHint = path.basename(localPath, path.extname(localPath));

  const filename = path.basename(localPath);
  const fileSlug = slug(titleHint || filename);
  const ext = path.extname(filename).toLowerCase().replace(/^\./, "") || "mp4";

  // Insert asset stub first to mint an asset_id, then build the R2 key with it.
  const insert = db.prepare(
    `INSERT INTO assets
       (path, type, title, idea_id, script_id, status, local_path, variant_label, duration_seconds, render_meta_json)
     VALUES (?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?)`,
  );

  // Generate a unique placeholder path; we'll update after we know the id.
  const placeholderKey = `ready/_pending/${Date.now()}-${filename}`;
  const result = insert.run(
    placeholderKey,
    type,
    titleHint,
    projectId,
    scriptId,
    localPath,
    body.variant_label ?? null,
    body.duration_seconds ?? null,
    body.render_meta ? JSON.stringify(body.render_meta) : null,
  );
  const assetId = Number(result.lastInsertRowid);

  // Build canonical R2 key once we have the asset_id.
  const projectSeg = projectId ?? "unlinked";
  const r2Key = `ready/${projectSeg}/${assetId}-${fileSlug}.${ext}`;

  let url: string;
  try {
    url = await uploadFile(localPath, r2Key);
  } catch (err) {
    db.prepare("DELETE FROM assets WHERE id = ?").run(assetId);
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `upload failed: ${msg}` }, { status: 500 });
  }

  db.prepare("UPDATE assets SET path = ?, url = ? WHERE id = ?").run(r2Key, url, assetId);

  const asset = db.prepare("SELECT * FROM assets WHERE id = ?").get(assetId);
  return NextResponse.json({ asset_id: assetId, key: r2Key, url, asset }, { status: 201 });
}
