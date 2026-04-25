export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { ProjectKanban, type ProjectRow } from "@/components/project-kanban";

const COLUMN_KEYS = [
  "draft",
  "scripted",
  "filming",
  "editing",
  "ready",
  "scheduled",
  "posted",
  "archived",
] as const;

export default async function ProjectsPage() {
  type Row = {
    id: number;
    title: string;
    hook: string | null;
    pillar: string | null;
    archived: number;
    source_type: string | null;
    source_url: string | null;
    modeled_after: string | null;
    notes: string | null;
    computed_status: string;
    script_count: number;
    asset_count: number;
    post_count: number;
    latest_thumbnail: string | null;
    has_reel_script: number;
    has_yt_script: number;
    has_carousel_script: number;
    posted_platforms: string | null;
    latest_views: number | null;
  };

  const rows = db
    .prepare(
      `
      SELECT i.id, i.title, i.hook, i.pillar, i.archived,
             i.source_type, i.source_url, i.modeled_after, i.notes,
             v.status AS computed_status,
             (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count,
             (SELECT COUNT(*) FROM assets a WHERE a.idea_id = i.id AND (a.path NOT LIKE 'stub:%' OR a.path IS NULL)) AS asset_count,
             (SELECT COUNT(*) FROM posts po
                JOIN assets a2 ON po.asset_id = a2.id
                WHERE a2.idea_id = i.id AND po.status = 'success') AS post_count,
             (SELECT a3.url FROM assets a3
                WHERE a3.idea_id = i.id AND a3.url IS NOT NULL AND a3.path NOT LIKE 'stub:%'
                ORDER BY a3.created_at DESC LIMIT 1) AS latest_thumbnail,
             EXISTS(SELECT 1 FROM scripts s2 WHERE s2.idea_id = i.id AND s2.variant = 'reel') AS has_reel_script,
             EXISTS(SELECT 1 FROM scripts s3 WHERE s3.idea_id = i.id AND s3.variant = 'youtube') AS has_yt_script,
             EXISTS(SELECT 1 FROM scripts s4 WHERE s4.idea_id = i.id AND s4.variant = 'carousel') AS has_carousel_script,
             (SELECT GROUP_CONCAT(DISTINCT po2.platform) FROM posts po2
                JOIN assets a4 ON po2.asset_id = a4.id
                WHERE a4.idea_id = i.id AND po2.status = 'success') AS posted_platforms,
             (SELECT MAX(m.views) FROM metrics m
                JOIN posts po3 ON m.post_id = po3.id
                JOIN assets a5 ON po3.asset_id = a5.id
                WHERE a5.idea_id = i.id) AS latest_views
      FROM ideas i
      LEFT JOIN v_project_status v ON v.project_id = i.id
      ORDER BY i.created_at DESC, i.id DESC
      `,
    )
    .all() as Row[];

  const projects: ProjectRow[] = rows.map((r) => ({
    id: r.id,
    title: r.title,
    hook: r.hook,
    pillar: r.pillar,
    archived: r.archived === 1,
    source_type: r.source_type,
    source_url: r.source_url,
    modeled_after: r.modeled_after,
    notes: r.notes,
    status: r.computed_status,
    script_count: r.script_count,
    asset_count: r.asset_count,
    post_count: r.post_count,
    thumbnail_url: r.latest_thumbnail,
    has_reel_script: r.has_reel_script === 1,
    has_yt_script: r.has_yt_script === 1,
    has_carousel_script: r.has_carousel_script === 1,
    posted_platforms: r.posted_platforms?.split(",").filter(Boolean) ?? [],
    latest_views: r.latest_views,
  }));

  // Group into columns; archived projects only land in Archived column.
  const columns: Record<string, ProjectRow[]> = Object.fromEntries(
    COLUMN_KEYS.map((k) => [k, [] as ProjectRow[]]),
  );
  for (const p of projects) {
    if (p.archived) {
      columns.archived.push(p);
      continue;
    }
    if (columns[p.status]) columns[p.status].push(p);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2
          className="text-lg font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.04em" }}
        >
          PROJECTS
        </h2>
        <p className="text-xs text-muted-foreground pt-1 font-light">
          Every content project. Status auto-computed from scripts, assets, and posts.
          Drag to <span style={{ color: "var(--brand)" }}>Archived</span> to hide.
        </p>
      </div>
      <ProjectKanban columns={columns} />
    </div>
  );
}
