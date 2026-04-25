"use client";

import * as React from "react";
import { Search, X, Loader2 } from "lucide-react";

type ScriptRow = {
  id: number;
  idea_id: number;
  variant: string; // 'reel' | 'youtube'
  body: string;
  word_count: number | null;
  updated_at: string;
  idea_title: string;
  idea_hook: string | null;
  idea_pillar: string | null;
};

type Step = "pick" | "edit" | "result";

export function CarouselCreateDialog({
  initialIdeaId,
  initialVariant,
  onClose,
  onCreated,
}: {
  initialIdeaId?: number;
  initialVariant?: "reel" | "youtube";
  onClose: () => void;
  onCreated?: (result: { idea_id: number; body: string }) => void;
}) {
  const [scripts, setScripts] = React.useState<ScriptRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");
  const [variantFilter, setVariantFilter] = React.useState<"all" | "reel" | "youtube">(
    initialVariant ?? "all",
  );
  const [step, setStep] = React.useState<Step>(initialIdeaId ? "edit" : "pick");
  const [selected, setSelected] = React.useState<ScriptRow | null>(null);
  const [editedBody, setEditedBody] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  const [carouselBody, setCarouselBody] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetch("/api/scripts/list")
      .then((r) => r.json())
      .then((d) => {
        const all = (d.scripts ?? []) as ScriptRow[];
        setScripts(all);
        if (initialIdeaId) {
          const variant = initialVariant ?? "reel";
          const match = all.find((s) => s.idea_id === initialIdeaId && s.variant === variant);
          if (match) {
            setSelected(match);
            setEditedBody(match.body);
          }
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [initialIdeaId, initialVariant]);

  const filtered = React.useMemo(() => {
    let r = scripts;
    if (variantFilter !== "all") r = r.filter((s) => s.variant === variantFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(
        (s) =>
          s.idea_title.toLowerCase().includes(q) ||
          s.idea_hook?.toLowerCase().includes(q) ||
          s.body.toLowerCase().includes(q),
      );
    }
    return r;
  }, [scripts, variantFilter, search]);

  const grouped = React.useMemo(() => {
    return {
      reel: filtered.filter((s) => s.variant === "reel"),
      youtube: filtered.filter((s) => s.variant === "youtube"),
    };
  }, [filtered]);

  function pickScript(s: ScriptRow) {
    setSelected(s);
    setEditedBody(s.body);
    setStep("edit");
  }

  async function generate() {
    if (!selected || generating) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch("/api/ideas/carousel", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          idea_id: selected.idea_id,
          override_body: editedBody.trim() === selected.body.trim() ? undefined : editedBody,
          source_variant: selected.variant,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Generation failed");
      setCarouselBody(data.body);
      setStep("result");
      onCreated?.({ idea_id: selected.idea_id, body: data.body });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="font-medium">
            {step === "pick" && "Create carousel — pick a script"}
            {step === "edit" && "Create carousel — review source"}
            {step === "result" && "Carousel created"}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-muted/40"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="text-xs text-red-400 border border-red-500/40 bg-red-500/10 rounded p-2">
              {error}
            </div>
          )}

          {step === "pick" && (
            <>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search ideas or scripts…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
                  />
                </div>
                <select
                  value={variantFilter}
                  onChange={(e) => setVariantFilter(e.target.value as typeof variantFilter)}
                  className="px-3 py-2 rounded-md border border-border bg-background text-sm"
                >
                  <option value="all">All</option>
                  <option value="reel">Short-form</option>
                  <option value="youtube">Long-form</option>
                </select>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  <Loader2 className="size-4 animate-spin mr-2" /> Loading scripts…
                </div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-12 text-sm text-muted-foreground border border-dashed border-border rounded">
                  No scripts found.
                </div>
              ) : (
                <div className="space-y-4">
                  {(["reel", "youtube"] as const).map((v) =>
                    grouped[v].length > 0 ? (
                      <div key={v}>
                        <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-2">
                          {v === "reel" ? "Short-form scripts" : "Long-form scripts"} ({grouped[v].length})
                        </div>
                        <div className="space-y-1.5">
                          {grouped[v].map((s) => (
                            <button
                              key={s.id}
                              type="button"
                              onClick={() => pickScript(s)}
                              className="w-full text-left p-3 rounded border border-border bg-background hover:border-[var(--brand)]/60 transition-colors"
                            >
                              <div className="text-sm font-medium truncate">{s.idea_title}</div>
                              <div className="text-xs text-muted-foreground line-clamp-2 mt-1">
                                {s.body.slice(0, 200)}
                              </div>
                              <div className="text-[10px] font-mono text-muted-foreground/70 mt-1">
                                {s.word_count ?? 0} words · {new Date(s.updated_at).toLocaleDateString()}
                                {s.idea_pillar && ` · ${s.idea_pillar}`}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null,
                  )}
                </div>
              )}
            </>
          )}

          {step === "edit" && selected && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                <span className="font-mono uppercase mr-2">
                  {selected.variant === "reel" ? "short-form" : "long-form"}
                </span>
                <span className="font-medium text-foreground">{selected.idea_title}</span>
              </div>
              <div className="text-[11px] text-muted-foreground">
                Edit the source script before generating. Leave unchanged to use as-is.
              </div>
              <textarea
                value={editedBody}
                onChange={(e) => setEditedBody(e.target.value)}
                rows={14}
                className="w-full p-3 rounded border border-border bg-background text-sm font-mono focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
              />
            </div>
          )}

          {step === "result" && (
            <div className="space-y-3">
              <div className="text-xs text-emerald-400">
                Carousel saved to scripts (variant: carousel) for idea #{selected?.idea_id}.
              </div>
              <pre className="whitespace-pre-wrap text-sm font-mono p-3 rounded border border-border bg-background max-h-[50vh] overflow-y-auto">
                {carouselBody}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border">
          <div className="text-[10px] font-mono text-muted-foreground">
            {step === "pick" && `${filtered.length} script${filtered.length === 1 ? "" : "s"}`}
            {step === "edit" && selected && `${editedBody.split(/\s+/).filter(Boolean).length} words`}
          </div>
          <div className="flex gap-2">
            {step === "edit" && !initialIdeaId && (
              <button
                type="button"
                onClick={() => setStep("pick")}
                className="px-3 py-1.5 text-sm rounded border border-border hover:bg-muted/40"
              >
                Back
              </button>
            )}
            {step === "edit" && (
              <button
                type="button"
                onClick={generate}
                disabled={generating || !editedBody.trim()}
                className="px-3 py-1.5 text-sm rounded bg-[var(--brand)] text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
              >
                {generating && <Loader2 className="size-3.5 animate-spin" />}
                Generate carousel
              </button>
            )}
            {step === "result" && (
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-sm rounded bg-[var(--brand)] text-white hover:opacity-90"
              >
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
