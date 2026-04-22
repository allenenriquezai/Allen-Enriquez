"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { IdeaCard, type IdeaCardData } from "@/components/idea-card";
import { cn } from "@/lib/utils";

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "new", label: "New" },
  { value: "picked", label: "Picked" },
  { value: "bookmarked", label: "Bookmarked" },
  { value: "dismissed", label: "Dismissed" },
];

export function IdeationClient({
  ideas,
  pillars,
  status,
  pillar,
}: {
  ideas: IdeaCardData[];
  pillars: string[];
  status: string;
  pillar: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [toast, setToast] = useState<string | null>(null);
  const [reseeding, setReseeding] = useState(false);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams?.toString() ?? "");
    if (value === "all") next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    startTransition(() => router.push(qs ? `/ideation?${qs}` : "/ideation"));
  }

  function flashToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  async function reseed() {
    setReseeding(true);
    try {
      const res = await fetch("/api/ideation/reseed", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        flashToast(
          `Re-seeded: +${data.ideasInserted} ideas, +${data.scriptsInserted} scripts, +${data.researchIdeasInserted} research`,
        );
        startTransition(() => router.refresh());
      } else {
        flashToast(`Re-seed failed: ${data.error ?? "unknown"}`);
      }
    } finally {
      setReseeding(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold mr-3">Ideation</h1>
          <div className="flex items-center gap-1">
            {STATUS_CHIPS.map((c) => (
              <button
                key={c.value}
                onClick={() => setParam("status", c.value)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs transition-colors",
                  status === c.value
                    ? "border-foreground bg-foreground text-background"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {c.label}
              </button>
            ))}
          </div>
          {pillars.length > 0 && (
            <select
              value={pillar}
              onChange={(e) => setParam("pillar", e.target.value)}
              className="ml-2 h-7 rounded-md border border-input bg-transparent px-2 text-xs"
            >
              <option value="all">All pillars</option>
              {pillars.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled
            onClick={() =>
              flashToast("Phase 2: will run /content-research skill")
            }
            title="Stub — Phase 2"
          >
            Run research
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={reseeding || pending}
            onClick={reseed}
          >
            {reseeding ? "Re-seeding…" : "Re-seed from drafts"}
          </Button>
        </div>
      </div>

      {toast && (
        <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-foreground">
          {toast}
        </div>
      )}

      {ideas.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No ideas match. Try clearing filters or hit &ldquo;Re-seed from
          drafts&rdquo;.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {ideas.map((i) => (
            <IdeaCard key={i.id} idea={i} />
          ))}
        </div>
      )}
    </div>
  );
}
