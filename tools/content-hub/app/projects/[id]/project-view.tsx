"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Scissors,
  Video,
  FileText,
  Plus,
  Archive,
} from "lucide-react";
import { AssetTile, type Asset } from "@/components/asset-tile";
import { LibraryAddDialog } from "@/components/library-add-dialog";
import { PostView } from "@/app/library/[id]/post-view";

type Project = {
  id: number;
  title: string;
  hook: string | null;
  pillar: string | null;
  lane: string | null;
  modeled_after: string | null;
  source_type: string | null;
  source_url: string | null;
  notes: string | null;
  archived: boolean;
  status: string;
};

type Script = {
  id: number;
  idea_id: number;
  variant: string;
  body: string;
  word_count: number | null;
};

type IdeaListRow = { id: number; title: string };

const SCRIPT_VARIANTS: { key: string; label: string }[] = [
  { key: "reel", label: "Short-form" },
  { key: "youtube", label: "Long-form" },
  { key: "carousel", label: "Carousel" },
];

const STATUS_TONES: Record<string, string> = {
  draft: "text-muted-foreground border-border",
  scripted: "text-cyan-300 border-cyan-300/40",
  filming: "text-orange-300 border-orange-300/40",
  editing: "text-amber-300 border-amber-300/40",
  ready: "text-emerald-300 border-emerald-300/40",
  scheduled: "text-blue-300 border-blue-300/40",
  posted: "text-pink-300 border-pink-300/40",
  archived: "text-zinc-500 border-zinc-700",
};

export function ProjectView({
  project,
  scripts,
  assets,
  ideas,
}: {
  project: Project;
  scripts: Script[];
  assets: Asset[];
  ideas: IdeaListRow[];
}) {
  const router = useRouter();
  const [showUpload, setShowUpload] = React.useState(false);
  const [activeAssetId, setActiveAssetId] = React.useState<number | null>(() => {
    const withUrl = assets.find((a) => a.url);
    return withUrl?.id ?? assets[0]?.id ?? null;
  });
  const [busyStage, setBusyStage] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);

  const activeAsset = React.useMemo(
    () => assets.find((a) => a.id === activeAssetId) ?? null,
    [assets, activeAssetId],
  );

  const initialScripts = React.useMemo(
    () => scripts.map((s) => ({ id: s.id, idea_id: s.idea_id, variant: s.variant, body: s.body })),
    [scripts],
  );

  const byVariant = React.useMemo(() => {
    const map = new Map<string, Script>();
    for (const s of scripts) map.set(s.variant, s);
    return map;
  }, [scripts]);

  const showFilming = project.status === "scripted";
  const showEditing = project.status === "scripted" || project.status === "filming";

  const advance = async (phase: "filming" | "editing") => {
    setBusyStage(phase);
    try {
      await fetch(`/api/projects/${project.id}/state`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase }),
      });
      router.refresh();
    } finally {
      setBusyStage(null);
    }
  };

  const archive = async () => {
    if (archiving) return;
    if (!confirm("Archive this project? It will move to the Archived column.")) return;
    setArchiving(true);
    try {
      await fetch(`/api/ideas/${project.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived: 1 }),
      });
      router.push("/projects");
    } finally {
      setArchiving(false);
    }
  };

  const tone = STATUS_TONES[project.status] ?? STATUS_TONES.draft;

  return (
    <div className="flex flex-col gap-6 pb-32">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <Link
          href="/projects"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Projects
        </Link>
        <button
          type="button"
          onClick={archive}
          disabled={archiving || project.archived}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40"
        >
          <Archive className="size-3.5" />
          {project.archived ? "Archived" : "Archive"}
        </button>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1.5 min-w-0">
            <h1 className="text-2xl font-semibold leading-tight">{project.title}</h1>
            {project.hook && (
              <p className="text-sm text-muted-foreground italic">{project.hook}</p>
            )}
            <div className="flex flex-wrap gap-1.5 items-center pt-1 text-[11px] font-mono">
              <span
                className={`px-2 py-0.5 rounded border uppercase tracking-wider ${tone}`}
              >
                {project.status}
              </span>
              {project.pillar && (
                <span className="px-2 py-0.5 rounded bg-muted/40 text-muted-foreground uppercase">
                  {project.pillar}
                </span>
              )}
              {project.modeled_after && (
                <span className="text-muted-foreground">@{project.modeled_after}</span>
              )}
              {project.source_url && (
                <a
                  href={project.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-[color:var(--brand)] inline-flex items-center gap-1"
                >
                  source <ExternalLink className="size-3" />
                </a>
              )}
            </div>
          </div>

          {/* Stage advance */}
          {(showFilming || showEditing) && (
            <div className="flex gap-2">
              {showFilming && (
                <button
                  type="button"
                  onClick={() => advance("filming")}
                  disabled={busyStage !== null}
                  className="flex items-center gap-1.5 rounded-md border border-orange-300/40 px-3 py-1.5 text-xs uppercase text-orange-300 hover:bg-orange-300/10 disabled:opacity-40"
                  style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.06em" }}
                >
                  <Video className="size-3.5" />
                  {busyStage === "filming" ? "…" : "Mark Filming"}
                </button>
              )}
              {showEditing && (
                <button
                  type="button"
                  onClick={() => advance("editing")}
                  disabled={busyStage !== null}
                  className="flex items-center gap-1.5 rounded-md border border-amber-300/40 px-3 py-1.5 text-xs uppercase text-amber-300 hover:bg-amber-300/10 disabled:opacity-40"
                  style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.06em" }}
                >
                  <Scissors className="size-3.5" />
                  {busyStage === "editing" ? "…" : "Mark Editing"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Scripts panel */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2
            className="text-sm font-semibold uppercase tracking-wider text-muted-foreground"
            style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.08em" }}
          >
            Scripts
          </h2>
          <Link
            href={`/scripts/${project.id}`}
            className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
          >
            <FileText className="size-3" /> Open editor
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {SCRIPT_VARIANTS.map((v) => {
            const s = byVariant.get(v.key);
            return (
              <Link
                key={v.key}
                href={`/scripts/${project.id}`}
                className="rounded-md border border-border bg-card hover:border-[color:var(--brand)]/50 transition-colors p-3 flex flex-col gap-1"
              >
                <span className="text-xs font-mono uppercase text-muted-foreground">
                  {v.label}
                </span>
                {s ? (
                  <>
                    <span className="text-[11px] text-emerald-400 font-mono">
                      {s.word_count ?? "—"} words
                    </span>
                    <span className="text-[11px] text-muted-foreground line-clamp-2">
                      {s.body.slice(0, 120)}
                    </span>
                  </>
                ) : (
                  <span className="text-[11px] text-muted-foreground/60 italic">
                    No script — click to create
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </section>

      {/* Media panel */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2
            className="text-sm font-semibold uppercase tracking-wider text-muted-foreground"
            style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.08em" }}
          >
            Media ({assets.length})
          </h2>
          <button
            type="button"
            onClick={() => setShowUpload(true)}
            className="text-xs text-[color:var(--brand)] hover:underline inline-flex items-center gap-1"
          >
            <Plus className="size-3" /> Upload
          </button>
        </div>
        {assets.length === 0 ? (
          <div className="rounded-md border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
            No media yet. Upload a video or image to start posting.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {assets.map((a) => {
              const isActive = a.id === activeAssetId;
              return (
                <div
                  key={a.id}
                  className={`relative rounded-lg transition-all ${
                    isActive ? "ring-2 ring-[color:var(--brand)] ring-offset-2 ring-offset-background" : ""
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setActiveAssetId(a.id)}
                    className="absolute top-2 left-2 z-20 px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border bg-black/70 text-white/90 hover:bg-black/90 border-white/20"
                  >
                    {isActive ? "Posting" : "Use"}
                  </button>
                  <AssetTile asset={a} onChange={() => router.refresh()} />
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Post bar — only show when we have an active asset with a URL */}
      {activeAsset && activeAsset.url ? (
        <section className="flex flex-col gap-3 pt-4 border-t border-border">
          <h2
            className="text-sm font-semibold uppercase tracking-wider text-muted-foreground"
            style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.08em" }}
          >
            Post
          </h2>
          <PostView
            key={activeAsset.id}
            asset={activeAsset}
            ideas={ideas}
            initialScripts={initialScripts}
          />
        </section>
      ) : assets.length > 0 ? (
        <section className="rounded-md border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
          Selected asset has no media URL. Upload via Library to make it postable.
        </section>
      ) : null}

      {showUpload && (
        <LibraryAddDialog
          defaultIdeaId={project.id}
          onDone={() => {
            setShowUpload(false);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}
