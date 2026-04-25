"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  ChevronRight,
  X,
  ExternalLink,
  Sparkles,
  RotateCcw,
  Plus,
  Link2,
} from "lucide-react";
import {
  DndContext,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { CarouselCreateDialog } from "@/components/carousel-create-dialog";
import type { ScheduledScript, KanbanIdea, WeekTheme } from "./page";

// ─── constants ───────────────────────────────────────────────────────────────

const COLUMNS = [
  {
    key: "new" as const,
    label: "New",
    statuses: ["new", "bookmarked"],
    targetStatus: "new",
  },
  {
    key: "needs_edit" as const,
    label: "Edits Needed",
    statuses: ["needs_edit"],
    targetStatus: "needs_edit",
  },
  {
    key: "picked" as const,
    label: "To Film",
    statuses: ["picked"],
    targetStatus: "picked",
  },
  {
    key: "dismissed" as const,
    label: "Rejects",
    statuses: ["dismissed"],
    targetStatus: "dismissed",
  },
  {
    key: "posted" as const,
    label: "Filmed / Posted",
    statuses: ["scripted", "filmed", "edited", "posted"],
    targetStatus: "filmed",
  },
];

type ColumnKey = (typeof COLUMNS)[number]["key"];

const PILLAR_COLORS: Record<string, string> = {
  fundamental: "bg-blue-500/15 text-blue-400",
  before_after_proof: "bg-emerald-500/15 text-emerald-400",
  behind_scenes: "bg-purple-500/15 text-purple-400",
  quick_tip: "bg-amber-500/15 text-amber-400",
  contrarian: "bg-rose-500/15 text-rose-400",
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// ─── helpers ─────────────────────────────────────────────────────────────────

function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function formatDayHeader(iso: string, label: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return `${label} ${d.getUTCDate()}`;
}

function formatWeekRange(monday: string, sunday: string): string {
  const m = new Date(monday + "T00:00:00Z");
  const s = new Date(sunday + "T00:00:00Z");
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-AU", {
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  return `${fmt(m)} – ${fmt(s)}`;
}

function slotLabel(slotType: string): string {
  const map: Record<string, string> = {
    reel_1: "SF1",
    reel_2: "SF2",
    youtube: "LF",
    carousel: "CA",
    fb_post: "FB",
  };
  return map[slotType] ?? slotType;
}

function ideaColumnKey(status: string): ColumnKey {
  if (status === "needs_edit") return "needs_edit";
  if (status === "picked") return "picked";
  if (status === "dismissed") return "dismissed";
  if (["scripted", "filmed", "edited", "posted"].includes(status)) return "posted";
  return "new";
}

function pillarBadge(pillar: string | null) {
  if (!pillar) return null;
  const style = PILLAR_COLORS[pillar] ?? "bg-zinc-500/15 text-zinc-400";
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${style}`}>
      {pillar}
    </span>
  );
}

// ─── Modal ───────────────────────────────────────────────────────────────────

function ScriptModal({
  idea,
  onClose,
  onSaved,
  onCarouselGenerated,
}: {
  idea: KanbanIdea;
  onClose: () => void;
  onSaved: (updates: { status: string; notes: string; reelBody: string }) => void;
  onCarouselGenerated: () => void;
}) {
  const [reelBody, setReelBody] = useState(idea.reelBody ?? "");
  const [notes, setNotes] = useState(idea.notes ?? "");
  const [status, setStatus] = useState(idea.status);
  const [hasCarousel, setHasCarousel] = useState(idea.hasCarousel);
  const [saving, setSaving] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [carouselDialogOpen, setCarouselDialogOpen] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleSave() {
    setSaving(true);
    setMsg(null);
    const res = await fetch(`/api/ideas/${idea.ideaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes, status }),
    });
    if (idea.scriptId && reelBody !== (idea.reelBody ?? "")) {
      await fetch(`/api/scripts/${idea.scriptId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: reelBody }),
      });
    }
    setSaving(false);
    if (!res.ok) {
      setMsg({ type: "err", text: "Save failed." });
      return;
    }
    setMsg({ type: "ok", text: "Saved." });
    onSaved({ status, notes, reelBody });
  }

  async function handleRewrite() {
    setRewriting(true);
    setMsg(null);
    const res = await fetch("/api/ideas/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea_ids: [idea.ideaId] }),
    });
    const json = await res.json();
    setRewriting(false);
    if (!res.ok || !json.results?.[0]) {
      setMsg({ type: "err", text: "Rewrite failed." });
      return;
    }
    setReelBody(json.results[0].body);
    setMsg({ type: "ok", text: "Rewritten." });
  }


  async function moveToStatus(newStatus: string) {
    setStatus(newStatus);
    setMsg(null);
    await fetch(`/api/ideas/${idea.ideaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    onSaved({ status: newStatus, notes, reelBody });
  }

  const currentCol = ideaColumnKey(status);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="pointer-events-auto w-full max-w-xl bg-background border rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3 shrink-0">
            <div className="flex flex-col gap-1.5 min-w-0">
              <h2 className="text-base font-semibold leading-snug">{idea.title}</h2>
              {idea.hook && (
                <p className="text-sm text-muted-foreground italic leading-snug">
                  {idea.hook}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                {pillarBadge(idea.pillar)}
                {idea.modeledAfter && (
                  <span className="text-xs text-muted-foreground/60">
                    via {idea.modeledAfter}
                  </span>
                )}
                {hasCarousel && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 font-medium">
                    CA ✓
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="shrink-0 text-muted-foreground hover:text-foreground mt-0.5"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>

          {/* Column move pills */}
          <div className="px-5 pb-3 shrink-0">
            <div className="flex gap-1.5 flex-wrap">
              {COLUMNS.map((col) => (
                <button
                  key={col.key}
                  onClick={() => moveToStatus(col.targetStatus)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    currentCol === col.key
                      ? "bg-foreground text-background border-foreground"
                      : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/40"
                  }`}
                >
                  {col.label}
                </button>
              ))}
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Short-form script
              </p>
              <Textarea
                value={reelBody}
                onChange={(e) => setReelBody(e.target.value)}
                placeholder="No short-form script yet — generate one in the full editor."
                rows={7}
                className="resize-y text-sm font-mono leading-relaxed"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Notes
              </p>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Feedback for AI rewrite, filming reminders…"
                rows={2}
                className="resize-y text-sm"
              />
            </div>
            {msg && (
              <p
                className={`text-xs ${
                  msg.type === "err" ? "text-destructive" : "text-green-500"
                }`}
              >
                {msg.text}
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 py-3 border-t shrink-0 flex items-center gap-2 flex-wrap">
            <Button size="sm" onClick={handleSave} disabled={saving} className="min-w-[60px]">
              {saving ? "Saving…" : "Save"}
            </Button>
            {reelBody ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleRewrite}
                disabled={rewriting}
              >
                {rewriting ? (
                  <RotateCcw size={12} className="mr-1 animate-spin" />
                ) : (
                  <Sparkles size={12} className="mr-1" />
                )}
                {rewriting ? "Rewriting…" : "Rewrite"}
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleRewrite}
                disabled={rewriting}
              >
                {rewriting ? (
                  <RotateCcw size={12} className="mr-1 animate-spin" />
                ) : (
                  <Sparkles size={12} className="mr-1" />
                )}
                {rewriting ? "Generating…" : "Generate Script"}
              </Button>
            )}
            {!hasCarousel && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCarouselDialogOpen(true)}
              >
                <Plus size={12} className="mr-1" />
                Carousel
              </Button>
            )}
            <Link
              href={`/scripts/${idea.ideaId}`}
              className="ml-auto flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ExternalLink size={12} />
              Full editor
            </Link>
          </div>
        </div>
      </div>
      {carouselDialogOpen && (
        <CarouselCreateDialog
          initialIdeaId={idea.ideaId}
          initialVariant="reel"
          onClose={() => setCarouselDialogOpen(false)}
          onCreated={() => {
            setHasCarousel(true);
            onCarouselGenerated();
          }}
        />
      )}
    </>
  );
}

// ─── KanbanCard ──────────────────────────────────────────────────────────────

function KanbanCard({
  idea,
  onOpen,
  onCarouselGen,
}: {
  idea: KanbanIdea;
  onOpen: () => void;
  onCarouselGen: () => Promise<void>;
}) {
  const [genLoading, setGenLoading] = useState(false);
  const showCarouselBtn =
    ["picked", "scripted", "filmed", "edited", "posted"].includes(idea.status) &&
    !idea.hasCarousel;

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `idea-${idea.ideaId}`,
    data: { idea },
  });

  async function handleCarousel(e: React.MouseEvent) {
    e.stopPropagation();
    setGenLoading(true);
    await onCarouselGen();
    setGenLoading(false);
  }

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      className={`rounded-xl border bg-card flex flex-col hover:border-foreground/20 transition-colors ${isDragging ? "opacity-40" : ""}`}
    >
      <button onClick={onOpen} className="text-left p-3 flex flex-col gap-1.5">
        <p className="text-sm font-medium leading-snug line-clamp-2">{idea.title}</p>
        {idea.hook && (
          <p className="text-xs text-muted-foreground italic line-clamp-1">{idea.hook}</p>
        )}
        <div className="flex flex-wrap items-center gap-1">
          {pillarBadge(idea.pillar)}
          {idea.modeledAfter && (
            <span className="text-xs text-muted-foreground/50 truncate max-w-[100px]">
              {idea.modeledAfter}
            </span>
          )}
          {idea.hasCarousel && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400">
              CA ✓
            </span>
          )}
          {!idea.reelBody && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
              no script
            </span>
          )}
        </div>
      </button>
      {showCarouselBtn && (
        <div className="px-3 pb-2.5">
          <button
            onClick={handleCarousel}
            disabled={genLoading}
            className="w-full text-xs text-muted-foreground hover:text-foreground border border-dashed border-border hover:border-foreground/30 rounded-lg px-2 py-1 transition-colors flex items-center justify-center gap-1"
          >
            {genLoading ? (
              <RotateCcw size={10} className="animate-spin" />
            ) : (
              <Plus size={10} />
            )}
            {genLoading ? "Generating…" : "Gen Carousel"}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── KanbanColumn ────────────────────────────────────────────────────────────

function KanbanColumn({
  col,
  ideas,
  onOpen,
  onCarouselGenerated,
  onRewriteAll,
  onGenerateIdeas,
  showGenPopover,
  onToggleGenPopover,
  rewritingAll,
  generatingIdeas,
}: {
  col: (typeof COLUMNS)[number];
  ideas: KanbanIdea[];
  onOpen: (idea: KanbanIdea) => void;
  onCarouselGenerated: (ideaId: number) => void;
  onRewriteAll: (ids: number[]) => void;
  onGenerateIdeas: (dayOfWeek?: string, count?: number) => void;
  showGenPopover: boolean;
  onToggleGenPopover: () => void;
  rewritingAll: boolean;
  generatingIdeas: boolean;
}) {
  const [selectedCount, setSelectedCount] = useState(10);
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `col-${col.key}`,
    data: { targetStatus: col.targetStatus },
  });

  return (
    <div
      ref={setDropRef}
      className={`flex flex-col gap-3 min-w-[200px] max-w-[200px] sm:min-w-[260px] sm:max-w-[260px] ${isOver ? "bg-muted/20 rounded-xl" : ""}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between sticky top-0 bg-background/95 backdrop-blur-sm py-1 z-10">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {col.label}
          </span>
          <span className="text-xs bg-muted text-muted-foreground rounded-full px-1.5 py-0.5 font-medium">
            {ideas.length}
          </span>
        </div>
        {col.key === "new" && (
          <div className="relative">
            <button
              onClick={onToggleGenPopover}
              disabled={generatingIdeas}
              title="Generate ideas with AI"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {generatingIdeas ? (
                <RotateCcw size={13} className="animate-spin" />
              ) : (
                <Sparkles size={13} />
              )}
            </button>
            {showGenPopover && (
              <div className="absolute right-0 top-6 z-20 w-56 bg-background border border-border rounded-xl shadow-xl p-3 flex flex-col gap-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Target day</p>
                <div className="flex flex-wrap gap-1">
                  {["Mon","Tue","Wed","Thu","Fri","Sat","Sun","Any"].map((d) => (
                    <button
                      key={d}
                      onClick={() => onGenerateIdeas(d === "Any" ? undefined : d, selectedCount)}
                      className="text-xs px-2 py-1 rounded-full border border-border hover:border-foreground/40 hover:text-foreground transition-colors text-muted-foreground"
                    >
                      {d}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <p className="text-xs text-muted-foreground">Count:</p>
                  {[5, 10, 20].map((n) => (
                    <button
                      key={n}
                      onClick={() => setSelectedCount(n)}
                      className={`text-xs px-2 py-0.5 rounded border transition-colors ${selectedCount === n ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {col.key === "needs_edit" && ideas.length > 0 && (
          <button
            onClick={() => onRewriteAll(ideas.map((i) => i.ideaId))}
            disabled={rewritingAll}
            title="Rewrite all with AI"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            {rewritingAll ? (
              <RotateCcw size={13} className="animate-spin" />
            ) : (
              <Sparkles size={13} />
            )}
          </button>
        )}
      </div>

      {/* Cards */}
      <div className="flex flex-col gap-2">
        {ideas.length === 0 ? (
          <p className="text-xs text-muted-foreground italic px-1 py-2">Empty</p>
        ) : (
          ideas.map((idea) => (
            <KanbanCard
              key={idea.ideaId}
              idea={idea}
              onOpen={() => onOpen(idea)}
              onCarouselGen={async () => {
                const res = await fetch("/api/ideas/carousel", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ idea_id: idea.ideaId }),
                });
                if (res.ok) onCarouselGenerated(idea.ideaId);
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ─── WeekPlanner ──────────────────────────────────────────────────────────────

const PILLARS = [
  "fundamental",
  "before_after_proof",
  "behind_scenes",
  "quick_tip",
  "contrarian",
] as const;

type ProposedTheme = {
  day: string;
  theme: string;
  pillar: string;
  rationale?: string;
};

function WeekPlanner({
  monday,
  sunday,
  weekThemes,
  weekIdeas,
  onNavigate,
  onOpenIdea,
  onIdeasGenerated,
  onThemesSaved,
}: {
  monday: string;
  sunday: string;
  weekThemes: WeekTheme[];
  weekIdeas: KanbanIdea[];
  onNavigate: (dir: -1 | 1) => void;
  onOpenIdea: (ideaId: number) => void;
  onIdeasGenerated: (newIdeas: KanbanIdea[]) => void;
  onThemesSaved: () => void;
}) {
  const router = useRouter();
  const [proposed, setProposed] = useState<ProposedTheme[] | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasSaved = weekThemes.length > 0;

  // Group ideas by day
  const ideasByDay = new Map<string, KanbanIdea[]>();
  for (const i of weekIdeas) {
    if (!i.dayOfWeek) continue;
    const list = ideasByDay.get(i.dayOfWeek) ?? [];
    list.push(i);
    ideasByDay.set(i.dayOfWeek, list);
  }

  async function suggestThemes() {
    setLoading("suggest");
    setError(null);
    try {
      const res = await fetch("/api/week-plan/suggest", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ week_start: monday }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "Suggest failed");
      setProposed(json.themes as ProposedTheme[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Suggest failed");
    } finally {
      setLoading(null);
    }
  }

  async function saveProposed(themes: ProposedTheme[]) {
    setLoading("save");
    setError(null);
    try {
      const res = await fetch("/api/week-plan/save", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ week_start: monday, themes }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? "Save failed");
      }
      setProposed(null);
      onThemesSaved();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(null);
    }
  }

  async function generateForDay(day: string) {
    setLoading(`gen-${day}`);
    setError(null);
    try {
      const res = await fetch("/api/week-plan/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ week_start: monday, day_of_week: day, count: 10 }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? "Generate failed");
      }
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setLoading(null);
    }
  }

  async function generateAll() {
    setLoading("gen-all");
    setError(null);
    try {
      const res = await fetch("/api/week-plan/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ week_start: monday, count: 10 }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? "Generate failed");
      }
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setLoading(null);
    }
  }

  async function replanWeek() {
    if (!confirm("Replan this week? Themes will be cleared. Existing ideas stay.")) return;
    setLoading("replan");
    try {
      await fetch(`/api/week-plan/save?week_start=${monday}`, { method: "DELETE" });
      onThemesSaved();
      router.refresh();
    } finally {
      setLoading(null);
    }
  }

  // Suppress unused-variable warning for onIdeasGenerated — kept in API for future inline-add
  void onIdeasGenerated;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" onClick={() => onNavigate(-1)} aria-label="Previous week">
          <ChevronLeft size={16} />
        </Button>
        <p className="text-sm font-medium flex-1 text-center">{formatWeekRange(monday, sunday)}</p>
        <Button variant="outline" size="icon" onClick={() => onNavigate(1)} aria-label="Next week">
          <ChevronRight size={16} />
        </Button>
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {/* No themes yet, no proposal */}
      {!hasSaved && !proposed && (
        <div className="flex flex-col items-center gap-3 py-12 border border-dashed rounded-xl">
          <p className="text-sm text-muted-foreground">No plan for this week yet.</p>
          <Button onClick={suggestThemes} disabled={loading === "suggest"}>
            <Sparkles size={14} className="mr-1.5" />
            {loading === "suggest" ? "Thinking…" : "Plan this week"}
          </Button>
        </div>
      )}

      {/* Proposal pending review */}
      {proposed && (
        <ProposedReview
          monday={monday}
          proposed={proposed}
          onChange={setProposed}
          onConfirm={() => saveProposed(proposed)}
          onCancel={() => setProposed(null)}
          saving={loading === "save"}
        />
      )}

      {/* Saved themes — generate + view ideas */}
      {hasSaved && !proposed && (
        <>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              {weekThemes.filter((t) => t.ideasGenerated).length} / {weekThemes.length} days have ideas
            </p>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={replanWeek} disabled={loading === "replan"}>
                {loading === "replan" ? "Clearing…" : "Replan"}
              </Button>
              <Button size="sm" onClick={generateAll} disabled={loading === "gen-all"}>
                <Sparkles size={12} className="mr-1" />
                {loading === "gen-all" ? "Generating…" : "Generate all"}
              </Button>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            {DAY_LABELS.map((label, i) => {
              const iso = addDays(monday, i);
              const t = weekThemes.find((x) => x.day === label);
              const dayIdeas = ideasByDay.get(label) ?? [];
              if (!t) return null;
              return (
                <div key={label} className="flex flex-col gap-2 rounded-xl border bg-card p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {formatDayHeader(iso, label)}
                      </p>
                      <p className="text-sm font-medium">{t.theme}</p>
                      {t.pillar && (
                        <span className={`self-start text-xs px-1.5 py-0.5 rounded-full font-medium ${PILLAR_COLORS[t.pillar] ?? "bg-zinc-500/15 text-zinc-400"}`}>
                          {t.pillar}
                        </span>
                      )}
                      {t.notes && (
                        <p className="text-xs text-muted-foreground italic mt-1">{t.notes}</p>
                      )}
                    </div>
                    {!t.ideasGenerated ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => generateForDay(label)}
                        disabled={loading === `gen-${label}`}
                        className="shrink-0"
                      >
                        {loading === `gen-${label}` ? (
                          <RotateCcw size={12} className="mr-1 animate-spin" />
                        ) : (
                          <Sparkles size={12} className="mr-1" />
                        )}
                        {loading === `gen-${label}` ? "Generating…" : "Generate 10"}
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground shrink-0">
                        {dayIdeas.length} ideas
                      </span>
                    )}
                  </div>

                  {dayIdeas.length > 0 && (
                    <div className="flex flex-col gap-1.5 mt-1 pl-1 border-l-2 border-border">
                      {dayIdeas.map((idea) => (
                        <button
                          key={idea.ideaId}
                          onClick={() => onOpenIdea(idea.ideaId)}
                          className="text-left px-2 py-1.5 rounded-lg hover:bg-muted/40 transition-colors flex flex-col gap-0.5"
                        >
                          <p className="text-sm leading-snug line-clamp-2">{idea.title}</p>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {idea.hook && (
                              <span className="text-xs text-muted-foreground italic line-clamp-1">
                                {idea.hook}
                              </span>
                            )}
                            {idea.reelBody ? (
                              <Badge variant="outline" className="text-[10px] py-0">script</Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px] py-0 text-muted-foreground">no script</Badge>
                            )}
                            <Badge variant="outline" className="text-[10px] py-0">{idea.status}</Badge>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function ProposedReview({
  monday,
  proposed,
  onChange,
  onConfirm,
  onCancel,
  saving,
}: {
  monday: string;
  proposed: ProposedTheme[];
  onChange: (next: ProposedTheme[]) => void;
  onConfirm: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  function update(i: number, patch: Partial<ProposedTheme>) {
    const next = [...proposed];
    next[i] = { ...next[i], ...patch };
    onChange(next);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Review proposed plan</p>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
          <Button size="sm" onClick={onConfirm} disabled={saving}>
            {saving ? "Saving…" : "Confirm & save"}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {DAY_LABELS.map((label, i) => {
          const iso = addDays(monday, i);
          const t = proposed.find((p) => p.day === label) ?? {
            day: label,
            theme: "",
            pillar: "fundamental",
            rationale: "",
          };
          const idx = proposed.findIndex((p) => p.day === label);
          return (
            <div key={label} className="flex flex-col gap-1.5 rounded-lg border bg-card p-3">
              <div className="flex items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground w-20">
                  {formatDayHeader(iso, label)}
                </p>
                <input
                  value={t.theme}
                  onChange={(e) => idx >= 0 && update(idx, { theme: e.target.value })}
                  placeholder="Theme"
                  className="flex-1 bg-transparent text-sm font-medium focus:outline-none border-b border-transparent focus:border-border"
                />
                <select
                  value={t.pillar}
                  onChange={(e) => idx >= 0 && update(idx, { pillar: e.target.value })}
                  className="text-xs rounded border bg-transparent px-1.5 py-0.5"
                >
                  {PILLARS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              {t.rationale && (
                <p className="text-xs text-muted-foreground italic pl-22">{t.rationale}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export function ScriptsClient({
  monday,
  sunday,
  scheduled,
  kanbanIdeas,
  weekThemes,
}: {
  monday: string;
  sunday: string;
  scheduled: ScheduledScript[];
  kanbanIdeas: KanbanIdea[];
  weekThemes: WeekTheme[];
}) {
  void scheduled;
  const router = useRouter();
  const [view, setView] = useState<"kanban" | "week">("kanban");
  const [localIdeas, setLocalIdeas] = useState<KanbanIdea[]>(kanbanIdeas);
  const [modalIdea, setModalIdea] = useState<KanbanIdea | null>(null);
  const [generatingIdeas, setGeneratingIdeas] = useState(false);
  const [rewritingAll, setRewritingAll] = useState(false);
  const [genPopover, setGenPopover] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [backfilling, setBackfilling] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const idea = (active.data.current as { idea: KanbanIdea }).idea;
    const targetStatus = (over.data.current as { targetStatus: string }).targetStatus;
    if (ideaColumnKey(idea.status) === ideaColumnKey(targetStatus)) return;
    updateIdea(idea.ideaId, { status: targetStatus });
    await fetch(`/api/ideas/${idea.ideaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: targetStatus }),
    });
    router.refresh();
  }

  function navigate(dir: -1 | 1) {
    router.push(`/scripts?week=${addDays(monday, dir * 7)}`);
  }

  const openIdea = useCallback(
    (ideaId: number) => {
      const idea = localIdeas.find((i) => i.ideaId === ideaId);
      if (idea) setModalIdea(idea);
    },
    [localIdeas],
  );

  function updateIdea(
    ideaId: number,
    updates: Partial<KanbanIdea>,
  ) {
    setLocalIdeas((prev) =>
      prev.map((i) => (i.ideaId === ideaId ? { ...i, ...updates } : i)),
    );
    if (modalIdea?.ideaId === ideaId) {
      setModalIdea((prev) => (prev ? { ...prev, ...updates } : prev));
    }
  }

  async function handleGenerateIdeas(dayOfWeek?: string, count = 10) {
    setGeneratingIdeas(true);
    setGenPopover(false);
    const res = await fetch("/api/ideas/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count, day_of_week: dayOfWeek ?? null }),
    });
    setGeneratingIdeas(false);
    if (!res.ok) return;
    const json = await res.json();
    if (Array.isArray(json.ideas)) {
      setLocalIdeas((prev) => [...(json.ideas as KanbanIdea[]), ...prev]);
    }
  }

  async function handleRewriteAll(ids: number[]) {
    setRewritingAll(true);
    const res = await fetch("/api/ideas/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea_ids: ids }),
    });
    setRewritingAll(false);
    if (!res.ok) return;
    const json = await res.json();
    for (const result of json.results ?? []) {
      updateIdea(result.id, { reelBody: result.body });
    }
  }

  async function handleImportLink() {
    setImporting(true);
    setImportError(null);
    const res = await fetch("/api/ideas/import-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: importUrl }),
    });
    setImporting(false);
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setImportError((j as { error?: string }).error ?? "Import failed");
      return;
    }
    const j = await res.json();
    if (j.idea) {
      setLocalIdeas((prev) => [j.idea as KanbanIdea, ...prev]);
    }
    setImportUrl("");
    setImportOpen(false);
  }

  async function handleBackfillScripts() {
    setBackfilling(true);
    setBackfillMsg(null);
    try {
      const res = await fetch("/api/ideas/backfill-scripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 50 }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "Backfill failed");
      setBackfillMsg(`Generated ${json.generated} scripts`);
      router.refresh();
    } catch (e) {
      setBackfillMsg(e instanceof Error ? e.message : "Backfill failed");
    } finally {
      setBackfilling(false);
    }
  }

  // Group ideas into columns
  const columnIdeas = COLUMNS.reduce(
    (acc, col) => {
      acc[col.key] = localIdeas.filter((i) =>
        col.statuses.includes(i.status),
      );
      return acc;
    },
    {} as Record<ColumnKey, KanbanIdea[]>,
  );

  const totalIdeas = localIdeas.length;
  const totalScheduled = scheduled.length;
  const noScriptCount = localIdeas.filter((i) => !i.reelBody && i.status !== "dismissed").length;
  const weekIdeas = localIdeas.filter(
    (i) => i.dayOfWeek && DAY_LABELS.includes(i.dayOfWeek),
  );

  return (
    <>
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Scripts</h1>
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted-foreground hidden sm:block">
              {view === "kanban"
                ? `${totalIdeas} ideas`
                : `${totalScheduled} scheduled`}
            </p>
            {/* Backfill missing scripts */}
            {noScriptCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="text-xs gap-1.5"
                onClick={handleBackfillScripts}
                disabled={backfilling}
                title={`${noScriptCount} ideas have no short-form script`}
              >
                {backfilling ? (
                  <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                {backfilling ? "Generating…" : `Fill ${noScriptCount} scripts`}
              </Button>
            )}
            {/* Import Link */}
            <Button
              variant="outline"
              size="sm"
              className="text-xs gap-1.5"
              onClick={() => { setImportOpen((v) => !v); setImportError(null); }}
            >
              <Link2 className="h-3.5 w-3.5" />
              Import Link
            </Button>
            {/* View toggle */}
            <div className="flex rounded-lg border overflow-hidden text-xs">
              <button
                onClick={() => setView("kanban")}
                className={`px-3 py-1.5 transition-colors ${
                  view === "kanban"
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Kanban
              </button>
              <button
                onClick={() => setView("week")}
                className={`px-3 py-1.5 transition-colors ${
                  view === "week"
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Week
              </button>
            </div>
          </div>
        </div>

        {/* Import Link dialog */}
        {importOpen && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2 p-3 rounded-lg border bg-muted/30">
              <input
                type="url"
                placeholder="Paste TikTok, YouTube, or Facebook link…"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !importing && handleImportLink()}
                className="flex-1 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
                autoFocus
              />
              <Button
                size="sm"
                className="text-xs shrink-0"
                onClick={handleImportLink}
                disabled={importing || !importUrl.trim()}
              >
                {importing ? "Transcribing…" : "Import"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="shrink-0"
                onClick={() => { setImportOpen(false); setImportError(null); setImportUrl(""); }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            {importError && (
              <p className="text-xs text-red-400 px-1">{importError}</p>
            )}
          </div>
        )}

        {/* Kanban view */}
        {view === "kanban" && (
          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            <div className="flex gap-4 overflow-x-auto pb-6 -mx-1 px-1">
              {COLUMNS.map((col) => (
                <KanbanColumn
                  key={col.key}
                  col={col}
                  ideas={columnIdeas[col.key]}
                  onOpen={(idea) => setModalIdea(idea)}
                  onCarouselGenerated={(ideaId) =>
                    updateIdea(ideaId, { hasCarousel: true })
                  }
                  onRewriteAll={handleRewriteAll}
                  onGenerateIdeas={handleGenerateIdeas}
                  showGenPopover={col.key === "new" && genPopover}
                  onToggleGenPopover={() => setGenPopover((v) => !v)}
                  rewritingAll={rewritingAll}
                  generatingIdeas={generatingIdeas}
                />
              ))}
            </div>
          </DndContext>
        )}

        {backfillMsg && (
          <p className="text-xs text-muted-foreground">{backfillMsg}</p>
        )}

        {/* Week planner */}
        {view === "week" && (
          <WeekPlanner
            monday={monday}
            sunday={sunday}
            weekThemes={weekThemes}
            weekIdeas={weekIdeas}
            onNavigate={navigate}
            onOpenIdea={openIdea}
            onIdeasGenerated={(newIdeas) => {
              setLocalIdeas((prev) => [...newIdeas, ...prev]);
            }}
            onThemesSaved={() => {}}
          />
        )}
      </div>

      {/* Modal */}
      {modalIdea && (
        <ScriptModal
          idea={modalIdea}
          onClose={() => setModalIdea(null)}
          onSaved={(updates) => {
            updateIdea(modalIdea.ideaId, updates);
            if (updates.status) router.refresh();
          }}
          onCarouselGenerated={() => {
            updateIdea(modalIdea.ideaId, { hasCarousel: true });
          }}
        />
      )}
    </>
  );
}
