"use client";

import { useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { ProjectCard } from "./project-card";

export type ProjectRow = {
  id: number;
  title: string;
  hook: string | null;
  pillar: string | null;
  archived: boolean;
  source_type: string | null;
  source_url: string | null;
  modeled_after: string | null;
  notes: string | null;
  status: string;
  script_count: number;
  asset_count: number;
  post_count: number;
  thumbnail_url: string | null;
  has_reel_script: boolean;
  has_yt_script: boolean;
  has_carousel_script: boolean;
  posted_platforms: string[];
  latest_views: number | null;
};

export const COLUMNS: { key: string; label: string; tone: string }[] = [
  { key: "draft", label: "Draft", tone: "text-muted-foreground" },
  { key: "scripted", label: "Scripted", tone: "text-cyan-300" },
  { key: "filming", label: "Filming", tone: "text-orange-300" },
  { key: "editing", label: "Editing", tone: "text-amber-300" },
  { key: "ready", label: "Ready", tone: "text-emerald-300" },
  { key: "scheduled", label: "Scheduled", tone: "text-blue-300" },
  { key: "posted", label: "Posted", tone: "text-pink-300" },
  { key: "archived", label: "Archived", tone: "text-zinc-500" },
];

export function ProjectKanban({ columns }: { columns: Record<string, ProjectRow[]> }) {
  const [data, setData] = useState(columns);
  const [busyId, setBusyId] = useState<number | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const onDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const projectId = Number(active.id);
    const targetCol = String(over.id);
    if (targetCol !== "archived") return; // only archive drag is meaningful

    // Optimistic move into Archived column
    const sourceCol = Object.keys(data).find((k) => data[k].some((p) => p.id === projectId));
    if (!sourceCol || sourceCol === "archived") return;
    const project = data[sourceCol].find((p) => p.id === projectId);
    if (!project) return;

    setBusyId(projectId);
    setData((prev) => ({
      ...prev,
      [sourceCol]: prev[sourceCol].filter((p) => p.id !== projectId),
      archived: [{ ...project, status: "archived", archived: true }, ...prev.archived],
    }));

    try {
      await fetch(`/api/ideas/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived: 1 }),
      });
    } catch {
      // revert on failure
      setData((prev) => ({
        ...prev,
        archived: prev.archived.filter((p) => p.id !== projectId),
        [sourceCol]: [project, ...prev[sourceCol]],
      }));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <DndContext id="project-kanban" sensors={sensors} onDragEnd={onDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.key}
            id={col.key}
            label={col.label}
            tone={col.tone}
            projects={data[col.key] ?? []}
            busyId={busyId}
          />
        ))}
      </div>
    </DndContext>
  );
}

function KanbanColumn({
  id,
  label,
  tone,
  projects,
  busyId,
}: {
  id: string;
  label: string;
  tone: string;
  projects: ProjectRow[];
  busyId: number | null;
}) {
  return (
    <div
      data-droppable={id}
      id={id}
      className="flex-shrink-0 w-[280px] flex flex-col gap-2"
    >
      <div className="flex items-center justify-between px-2 py-1">
        <span
          className={`text-[0.72rem] uppercase tracking-wider ${tone}`}
          style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.08em" }}
        >
          {label}
        </span>
        <span className="text-[0.7rem] text-muted-foreground">{projects.length}</span>
      </div>
      <Droppable id={id}>
        <div className="flex flex-col gap-2 min-h-[60px] rounded-md p-1">
          {projects.length === 0 && (
            <p className="text-[0.7rem] text-muted-foreground/60 px-2 py-3 italic">empty</p>
          )}
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} dimmed={busyId === p.id} />
          ))}
        </div>
      </Droppable>
    </div>
  );
}

import { useDroppable } from "@dnd-kit/core";
function Droppable({ id, children }: { id: string; children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      className={isOver ? "bg-[color:var(--brand)]/10 rounded-md transition-colors" : ""}
    >
      {children}
    </div>
  );
}
