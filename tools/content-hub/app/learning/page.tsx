"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ReferenceCard, type LearningRef } from "@/components/reference-card";

const CATEGORIES = [
  { value: "viral_ref", label: "Viral References" },
  { value: "trending_topic", label: "Trending Topics" },
  { value: "competitor_post", label: "Competitor Posts" },
] as const;

export default function LearningPage() {
  const [refs, setRefs] = useState<LearningRef[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/learning", { cache: "no-store" });
    const json = await res.json();
    setRefs(json.refs ?? []);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  };

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
      if (res.ok) {
        flash("Sent to ideation");
      } else {
        flash("Sent to ideation (stub)");
      }
    } catch {
      flash("Sent to ideation (stub)");
    }
  };

  const removeRef = async (id: number) => {
    await fetch(`/api/learning/${id}`, { method: "DELETE" });
    load();
  };

  const reseed = async () => {
    flash("Re-seeding…");
    try {
      const res = await fetch("/api/learning/reseed", { method: "POST" });
      if (res.ok) {
        flash("Re-seeded from research.md");
        load();
      } else {
        flash("Reseed endpoint not wired — run `npm run seed` in terminal");
      }
    } catch {
      flash("Run `npm run seed` in terminal to re-seed");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Learning</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Viral refs + trends + competitor moves. Seeded from research.md.
          </p>
        </div>
        <Button variant="outline" onClick={reseed}>
          Re-seed from research.md
        </Button>
      </div>

      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-card ring-1 ring-foreground/10 px-4 py-2 rounded-lg text-sm shadow-lg">
          {toast}
        </div>
      )}

      <Tabs defaultValue="viral_ref">
        <TabsList>
          {CATEGORIES.map((c) => (
            <TabsTrigger key={c.value} value={c.value}>
              {c.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="viral_ref" className="mt-4">
          <SectionHeader
            title="Viral References"
            category="viral_ref"
            onSaved={load}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
            {viralRefs.map((r) => (
              <ReferenceCard
                key={r.id}
                ref={r}
                onCopyToIdeation={copyToIdeation}
                onDelete={removeRef}
              />
            ))}
            {viralRefs.length === 0 && <EmptyState />}
          </div>
        </TabsContent>

        <TabsContent value="trending_topic" className="mt-4">
          <SectionHeader
            title="Trending Topics"
            category="trending_topic"
            onSaved={load}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
            {trendingTopics.map((r) => (
              <TrendingCard
                key={r.id}
                ref={r}
                onCopyToIdeation={copyToIdeation}
                onDelete={removeRef}
              />
            ))}
            {trendingTopics.length === 0 && <EmptyState />}
          </div>
        </TabsContent>

        <TabsContent value="competitor_post" className="mt-4">
          <SectionHeader
            title="Competitor Posts"
            category="competitor_post"
            onSaved={load}
          />
          <div className="flex flex-col gap-2 mt-3">
            {competitorPosts.map((r) => (
              <Card key={r.id} size="sm">
                <CardContent className="pt-3 flex gap-3 items-start">
                  <div className="font-semibold min-w-24">{r.creator ?? "?"}</div>
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
            {competitorPosts.length === 0 && <EmptyState />}
          </div>
        </TabsContent>
      </Tabs>
    </div>
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
  // Allen-angle highlight: look for "Allen angle:" in notes.
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

function SectionHeader({
  title,
  category,
  onSaved,
}: {
  title: string;
  category: string;
  onSaved: () => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-semibold">{title}</h2>
      <AddReferenceDialog category={category} onSaved={onSaved} />
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

function EmptyState() {
  return (
    <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-6 text-center col-span-full">
      No entries. Add one or run <code className="font-mono">npm run seed</code>.
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
