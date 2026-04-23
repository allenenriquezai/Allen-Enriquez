"use client";

import { useCallback, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ReferenceCard, type LearningRef } from "@/components/reference-card";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CreatorPost = {
  id: number;
  post_id: string;
  creator: string;
  platform: string;
  url: string;
  title: string | null;
  description: string | null;
  thumbnail_url: string | null;
  posted_at: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration_sec: number | null;
  transcript: string | null;
  hook: string | null;
  topic: string | null;
  why_it_works: string | null;
  fetched_at: string;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtNum(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return s;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CreatorPostCard({ p }: { p: CreatorPost }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline">{p.creator}</Badge>
            <Badge variant="secondary">{p.platform}</Badge>
            <span className="text-xs text-muted-foreground">
              {fmtDate(p.posted_at)}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
            <span>👁 {fmtNum(p.view_count)}</span>
            <span>❤ {fmtNum(p.like_count)}</span>
            <span>💬 {fmtNum(p.comment_count)}</span>
          </div>
        </div>
        <CardTitle className="text-base leading-snug pt-2">
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--brand)]"
          >
            {p.title || p.hook || p.post_id}
          </a>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 flex gap-4">
        {p.thumbnail_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={p.thumbnail_url}
            alt=""
            className="w-28 h-auto rounded-md border border-border shrink-0 object-cover"
          />
        )}
        <div className="flex-1 flex flex-col gap-2 text-sm min-w-0">
          {p.hook && (
            <div>
              <div className="ae-mono-label pb-1">Hook</div>
              <p className="leading-snug">{p.hook}</p>
            </div>
          )}
          {p.topic && (
            <div>
              <div className="ae-mono-label pb-1">Topic</div>
              <p className="text-muted-foreground leading-snug">{p.topic}</p>
            </div>
          )}
          {p.why_it_works && (
            <div>
              <div
                className="ae-mono-label pb-1"
                style={{ color: "var(--brand)" }}
              >
                Why it works
              </div>
              <p className="text-muted-foreground leading-snug">
                {p.why_it_works}
              </p>
            </div>
          )}
          {p.transcript && (
            <details className="mt-2">
              <summary className="ae-mono-label cursor-pointer hover:text-[var(--brand)]">
                Transcript
              </summary>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground leading-relaxed font-sans max-h-64 overflow-auto">
                {p.transcript}
              </pre>
            </details>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function TrendingCard({
  ref: item,
  onCopyToIdeation,
  onDelete,
}: {
  ref: LearningRef;
  onCopyToIdeation: (r: LearningRef) => void;
  onDelete: (id: number) => void;
}) {
  let main = item.notes ?? "";
  let allenAngle: string | null = null;
  const idx = main.indexOf("Allen angle:");
  if (idx >= 0) {
    allenAngle = main.slice(idx + "Allen angle:".length).trim();
    main = main.slice(0, idx).replace(/\.\s*$/, "").trim();
  }
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>{item.title ?? "(untitled)"}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {main && <p className="text-sm text-muted-foreground">{main}</p>}
        {allenAngle && (
          <div
            className="text-sm border-l-2 pl-2 italic"
            style={{ borderColor: "var(--brand)", color: "var(--brand)" }}
          >
            Allen angle: {allenAngle}
          </div>
        )}
        <div className="flex gap-1.5 pt-1">
          <Button
            size="xs"
            variant="outline"
            onClick={() => onCopyToIdeation(item)}
          >
            Copy to Ideation
          </Button>
          <Button size="xs" variant="ghost" onClick={() => onDelete(item.id)}>
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-6 text-center col-span-full">
      {label}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function AddReferenceDialog({
  category,
  onSaved,
}: {
  category: string;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    url: "",
    creator: "",
    platform: "",
    title: "",
    notes: "",
  });

  const save = async () => {
    await fetch("/api/learning", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, category }),
    });
    setOpen(false);
    setForm({ url: "", creator: "", platform: "", title: "", notes: "" });
    onSaved();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button size="sm" variant="outline">
            Add reference
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add reference</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <Field label="Title">
            <Input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </Field>
          <Field label="URL">
            <Input
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder="https://..."
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Creator">
              <Input
                value={form.creator}
                onChange={(e) =>
                  setForm({ ...form, creator: e.target.value })
                }
              />
            </Field>
            <Field label="Platform">
              <Input
                value={form.platform}
                onChange={(e) =>
                  setForm({ ...form, platform: e.target.value })
                }
              />
            </Field>
          </div>
          <Field label="Notes">
            <Textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="min-h-24"
            />
          </Field>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={save}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main client component
// ---------------------------------------------------------------------------

const CREATOR_FILTER_ALL = "all";

export function InspirationClient({
  posts,
  refs: initialRefs,
}: {
  posts: CreatorPost[];
  refs: LearningRef[];
}) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [toast, setToast] = useState<string | null>(null);
  const [refs, setRefs] = useState<LearningRef[]>(initialRefs);
  const [creatorFilter, setCreatorFilter] = useState(CREATOR_FILTER_ALL);

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  };

  // Learning refs — reload from API after mutations
  const loadRefs = useCallback(async () => {
    const res = await fetch("/api/learning", { cache: "no-store" });
    const json = await res.json();
    setRefs(json.refs ?? []);
  }, []);

  const copyToIdeation = async (ref: LearningRef) => {
    const payload = {
      title: ref.title ?? "(untitled)",
      hook: ref.title ?? null,
      pillar: "research",
      lane: null,
      category: ref.category,
      modeled_after: ref.creator ?? null,
      source_platform: ref.platform ?? null,
      source_url: ref.url ?? null,
      batch: "learning",
      status: "new",
    };
    try {
      const res = await fetch("/api/ideas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      flash(res.ok ? "Sent to ideation" : "Sent to ideation (stub)");
    } catch {
      flash("Sent to ideation (stub)");
    }
  };

  const removeRef = async (id: number) => {
    await fetch(`/api/learning/${id}`, { method: "DELETE" });
    loadRefs();
  };

  const reseedLearning = async () => {
    flash("Re-seeding…");
    try {
      const res = await fetch("/api/learning/reseed", { method: "POST" });
      if (res.ok) {
        flash("Re-seeded from research.md");
        loadRefs();
      } else {
        flash("Run `npm run seed` in terminal to re-seed");
      }
    } catch {
      flash("Run `npm run seed` in terminal to re-seed");
    }
  };

  const refreshFeed = () => {
    startTransition(() => router.refresh());
  };

  // Derived
  const creators = useMemo(
    () => [CREATOR_FILTER_ALL, ...Array.from(new Set(posts.map((p) => p.creator)))],
    [posts],
  );

  const filteredPosts = useMemo(
    () =>
      creatorFilter === CREATOR_FILTER_ALL
        ? posts
        : posts.filter((p) => p.creator === creatorFilter),
    [posts, creatorFilter],
  );

  const viralRefs = useMemo(
    () => refs.filter((r) => r.category === "viral_ref"),
    [refs],
  );
  const trendingTopics = useMemo(
    () => refs.filter((r) => r.category === "trending_topic"),
    [refs],
  );
  const competitorPosts = useMemo(
    () => refs.filter((r) => r.category === "competitor_post"),
    [refs],
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-semibold">Inspiration</h1>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-card ring-1 ring-foreground/10 px-4 py-2 rounded-lg text-sm shadow-lg">
          {toast}
        </div>
      )}

      {/* Top-level tabs: Feed | Viral Refs | Trending | Competitors */}
      <Tabs defaultValue="feed">
        <TabsList>
          <TabsTrigger value="feed">
            Creator Feed
            {posts.length > 0 && (
              <span className="ml-1.5 text-[10px] text-muted-foreground">
                {posts.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="viral_ref">Viral Refs</TabsTrigger>
          <TabsTrigger value="trending_topic">Trending</TabsTrigger>
          <TabsTrigger value="competitor_post">Competitors</TabsTrigger>
        </TabsList>

        {/* ------------------------------------------------------------------ */}
        {/* CREATOR FEED                                                        */}
        {/* ------------------------------------------------------------------ */}
        <TabsContent value="feed" className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            {/* Creator filter chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              {creators.map((c) => (
                <button
                  key={c}
                  onClick={() => setCreatorFilter(c)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    creatorFilter === c
                      ? "border-foreground bg-foreground text-background"
                      : "border-border text-muted-foreground hover:text-foreground",
                  )}
                >
                  {c === CREATOR_FILTER_ALL ? "All" : c}
                </button>
              ))}
            </div>
            <Button size="sm" variant="outline" onClick={refreshFeed}>
              Refresh
            </Button>
          </div>

          {filteredPosts.length === 0 ? (
            <EmptyState label="No posts yet. Run python3 tools/creator_feed.py to fetch." />
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {filteredPosts.map((p) => (
                <CreatorPostCard key={p.id} p={p} />
              ))}
            </div>
          )}
        </TabsContent>

        {/* ------------------------------------------------------------------ */}
        {/* VIRAL REFS                                                          */}
        {/* ------------------------------------------------------------------ */}
        <TabsContent value="viral_ref" className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Viral References</h2>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={reseedLearning}>
                Re-seed
              </Button>
              <AddReferenceDialog category="viral_ref" onSaved={loadRefs} />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {viralRefs.map((r) => (
              <ReferenceCard
                key={r.id}
                ref={r}
                onCopyToIdeation={copyToIdeation}
                onDelete={removeRef}
              />
            ))}
            {viralRefs.length === 0 && (
              <EmptyState label="No viral refs. Add one or re-seed." />
            )}
          </div>
        </TabsContent>

        {/* ------------------------------------------------------------------ */}
        {/* TRENDING TOPICS                                                     */}
        {/* ------------------------------------------------------------------ */}
        <TabsContent value="trending_topic" className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Trending Topics</h2>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={reseedLearning}>
                Re-seed
              </Button>
              <AddReferenceDialog
                category="trending_topic"
                onSaved={loadRefs}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {trendingTopics.map((r) => (
              <TrendingCard
                key={r.id}
                ref={r}
                onCopyToIdeation={copyToIdeation}
                onDelete={removeRef}
              />
            ))}
            {trendingTopics.length === 0 && (
              <EmptyState label="No trending topics. Add one or re-seed." />
            )}
          </div>
        </TabsContent>

        {/* ------------------------------------------------------------------ */}
        {/* COMPETITOR POSTS                                                    */}
        {/* ------------------------------------------------------------------ */}
        <TabsContent value="competitor_post" className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Competitor Posts</h2>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={reseedLearning}>
                Re-seed
              </Button>
              <AddReferenceDialog
                category="competitor_post"
                onSaved={loadRefs}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {competitorPosts.map((r) => (
              <Card key={r.id} size="sm">
                <CardContent className="pt-3 flex gap-3 items-start">
                  <div className="font-semibold min-w-24">
                    {r.creator ?? "?"}
                  </div>
                  <div className="text-sm text-muted-foreground flex-1">
                    {r.notes}
                  </div>
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => removeRef(r.id)}
                  >
                    Delete
                  </Button>
                </CardContent>
              </Card>
            ))}
            {competitorPosts.length === 0 && (
              <EmptyState label="No competitor posts. Add one or re-seed." />
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
