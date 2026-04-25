export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import db from "@/lib/db";
import type { Asset, AssetPost } from "@/components/asset-tile";
import { ProjectView } from "./project-view";

type IdeaRow = {
  id: number;
  title: string;
  hook: string | null;
  pillar: string | null;
  lane: string | null;
  modeled_after: string | null;
  source_type: string | null;
  source_url: string | null;
  notes: string | null;
  archived: number;
};

type ScriptRow = {
  id: number;
  idea_id: number;
  variant: string;
  body: string;
  word_count: number | null;
};

type AssetRow = Omit<Asset, "posts">;
type IdeaListRow = { id: number; title: string };

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const projectId = Number(id);
  if (!Number.isFinite(projectId)) notFound();

  const project = db
    .prepare(
      `SELECT id, title, hook, pillar, lane, modeled_after, source_type, source_url, notes, archived
       FROM ideas WHERE id = ?`,
    )
    .get(projectId) as IdeaRow | undefined;
  if (!project) notFound();

  const status = (db
    .prepare("SELECT status FROM v_project_status WHERE project_id = ?")
    .get(projectId) as { status: string } | undefined)?.status ?? "draft";

  const scripts = db
    .prepare(
      `SELECT id, idea_id, variant, body, word_count FROM scripts WHERE idea_id = ?`,
    )
    .all(projectId) as ScriptRow[];

  const assetRows = db
    .prepare(
      `SELECT * FROM assets
       WHERE idea_id = ? AND (path NOT LIKE 'stub:%' OR path IS NULL)
       ORDER BY created_at DESC`,
    )
    .all(projectId) as AssetRow[];

  const assetIds = assetRows.map((a) => a.id);
  const posts = assetIds.length
    ? (db
        .prepare(
          `SELECT * FROM posts WHERE asset_id IN (${assetIds.map(() => "?").join(",")}) ORDER BY posted_at DESC`,
        )
        .all(...assetIds) as AssetPost[])
    : [];

  const assets: Asset[] = assetRows.map((row) => ({
    ...row,
    posts: posts.filter((p) => p.asset_id === row.id),
  }));

  const ideas = db
    .prepare("SELECT id, title FROM ideas ORDER BY created_at DESC")
    .all() as IdeaListRow[];

  return (
    <ProjectView
      project={{
        id: project.id,
        title: project.title,
        hook: project.hook,
        pillar: project.pillar,
        lane: project.lane,
        modeled_after: project.modeled_after,
        source_type: project.source_type,
        source_url: project.source_url,
        notes: project.notes,
        archived: project.archived === 1,
        status,
      }}
      scripts={scripts}
      assets={assets}
      ideas={ideas}
    />
  );
}
