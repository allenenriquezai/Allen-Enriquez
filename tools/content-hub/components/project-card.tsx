"use client";

import Link from "next/link";
import { useDraggable } from "@dnd-kit/core";
import { Check, Square, ExternalLink } from "lucide-react";
import type { ProjectRow } from "./project-kanban";

const PLATFORM_LABEL: Record<string, string> = {
  instagram: "IG",
  facebook: "FB",
  youtube: "YT",
  tiktok: "TT",
  x: "X",
};

function nFmt(n: number | null | undefined): string {
  if (n == null) return "";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "k";
  return String(n);
}

export function ProjectCard({ project, dimmed }: { project: ProjectRow; dimmed?: boolean }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: project.id,
  });

  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: dimmed ? 0.5 : isDragging ? 0.7 : 1,
    cursor: isDragging ? "grabbing" : "grab",
  };

  // Mini-checklist
  const checklist: { label: string; done: boolean }[] = [
    { label: "Reel", done: project.has_reel_script },
    { label: "YT", done: project.has_yt_script },
    { label: "Slides", done: project.has_carousel_script },
    { label: "Asset", done: project.asset_count > 0 },
    { label: "Posted", done: project.post_count > 0 },
  ];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="rounded-md border border-border bg-card hover:border-[color:var(--brand)]/50 transition-colors p-3 select-none"
    >
      {project.thumbnail_url && (
        <div
          className="aspect-video rounded-sm bg-cover bg-center mb-2"
          style={{ backgroundImage: `url(${project.thumbnail_url})` }}
        />
      )}
      <Link
        href={`/projects/${project.id}`}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        className="block"
      >
        <h3 className="text-sm font-medium leading-snug line-clamp-2 hover:text-[color:var(--brand)]">
          {project.title}
        </h3>
      </Link>

      {project.hook && (
        <p className="text-[0.7rem] text-muted-foreground mt-1 line-clamp-2 italic">
          {project.hook}
        </p>
      )}

      {project.source_type && project.source_type !== "raw" && (
        <div className="mt-2 flex items-center gap-1 text-[0.65rem]">
          <span
            className="px-1.5 py-0.5 rounded-sm bg-[color:var(--muted)]/40 uppercase"
            style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.06em" }}
          >
            {project.source_type.replace("_", " ")}
          </span>
          {project.modeled_after && (
            <span className="text-muted-foreground truncate">@{project.modeled_after}</span>
          )}
          {project.source_url && (
            <a
              href={project.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              className="text-muted-foreground hover:text-[color:var(--brand)]"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[0.65rem] text-muted-foreground">
        {checklist.map((c) => (
          <span key={c.label} className="inline-flex items-center gap-0.5">
            {c.done ? (
              <Check className="h-2.5 w-2.5 text-emerald-400" />
            ) : (
              <Square className="h-2.5 w-2.5 opacity-40" />
            )}
            <span className={c.done ? "text-foreground" : ""}>{c.label}</span>
          </span>
        ))}
      </div>

      {project.posted_platforms.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1 text-[0.6rem]">
          {project.posted_platforms.map((p) => (
            <span
              key={p}
              className="px-1.5 py-0.5 rounded-sm bg-[color:var(--brand)]/15 text-[color:var(--brand)]"
              style={{ fontFamily: "var(--font-roboto-mono)" }}
            >
              {PLATFORM_LABEL[p] ?? p}
            </span>
          ))}
          {project.latest_views != null && project.latest_views > 0 && (
            <span className="text-muted-foreground">{nFmt(project.latest_views)} views</span>
          )}
        </div>
      )}
    </div>
  );
}

