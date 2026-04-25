"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search, Plus } from "lucide-react";
import { AssetTile, type Asset } from "@/components/asset-tile";
import { CarouselCreateDialog } from "@/components/carousel-create-dialog";

type Tab = "shortform" | "longform" | "carousels";

const LONGFORM_THRESHOLD_SEC = 180; // 3 minutes

function classifyAsset(a: Asset): Tab {
  if (a.type === "carousel") return "carousels";
  if (a.duration_seconds && a.duration_seconds >= LONGFORM_THRESHOLD_SEC) return "longform";
  if (a.type === "youtube") return "longform";
  return "shortform";
}

export function LibraryGrid({ assets }: { assets: Asset[] }) {
  const router = useRouter();
  const [tab, setTab] = React.useState<Tab>("shortform");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [sortOrder, setSortOrder] = React.useState<"newest" | "oldest" | "unposted">("newest");
  const [showHidden, setShowHidden] = React.useState(false);
  const [carouselOpen, setCarouselOpen] = React.useState(false);

  const visibleAssets = React.useMemo(() => {
    // Always exclude raw thumbnails — they're upload artifacts, not content tiles
    const content = assets.filter((a) => a.type !== "thumbnail");
    return showHidden ? content : content.filter((a) => !a.hidden);
  }, [assets, showHidden]);

  const counts = React.useMemo(() => {
    const c = { shortform: 0, longform: 0, carousels: 0 };
    for (const a of visibleAssets) c[classifyAsset(a)]++;
    return c;
  }, [visibleAssets]);

  const hiddenCount = React.useMemo(
    () => assets.filter((a) => a.hidden).length,
    [assets],
  );

  const filtered = React.useMemo(() => {
    let result = visibleAssets.filter((a) => classifyAsset(a) === tab);

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) => a.title?.toLowerCase().includes(q) || a.path.toLowerCase().includes(q),
      );
    }

    if (sortOrder === "newest") {
      result = [...result].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    } else if (sortOrder === "oldest") {
      result = [...result].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    } else if (sortOrder === "unposted") {
      result = [...result].sort((a, b) => {
        const aPosted = a.posts.length === 0 ? 0 : 1;
        const bPosted = b.posts.length === 0 ? 0 : 1;
        if (aPosted !== bPosted) return aPosted - bPosted;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
    }
    return result;
  }, [visibleAssets, tab, searchQuery, sortOrder]);

  const TABS: Array<{ key: Tab; label: string; hint: string }> = [
    { key: "shortform", label: "Short-form", hint: "< 3 min" },
    { key: "longform", label: "Long-form", hint: "≥ 3 min" },
    { key: "carousels", label: "Carousels", hint: "images" },
  ];

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className="relative px-4 py-2.5 text-sm font-medium transition-colors"
              style={{
                color: active ? "var(--brand)" : "var(--muted-foreground)",
                borderBottom: active ? "2px solid var(--brand)" : "2px solid transparent",
                marginBottom: "-1px",
              }}
            >
              <span className="flex items-center gap-2">
                {t.label}
                <span className="text-[10px] font-mono text-muted-foreground/60">{t.hint}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/40">
                  {counts[t.key]}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search title or filename…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
          />
        </div>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}
          className="px-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="unposted">Unposted first</option>
        </select>
        <label className="flex items-center gap-2 text-xs text-muted-foreground select-none cursor-pointer px-2">
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(e) => setShowHidden(e.target.checked)}
          />
          Show hidden
          {hiddenCount > 0 && (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-muted/40">{hiddenCount}</span>
          )}
        </label>
        {tab === "carousels" && (
          <button
            type="button"
            onClick={() => setCarouselOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-md bg-[var(--brand)] text-white hover:opacity-90"
          >
            <Plus className="size-4" /> New carousel
          </button>
        )}
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-border rounded-lg">
          <p className="text-sm text-muted-foreground">
            {searchQuery ? "No matches in this tab." : `No ${TABS.find((t) => t.key === tab)?.label.toLowerCase()} yet.`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {filtered.map((a) => (
            <AssetTile key={a.id} asset={a} onChange={() => router.refresh()} />
          ))}
        </div>
      )}

      {carouselOpen && (
        <CarouselCreateDialog
          onClose={() => setCarouselOpen(false)}
          onCreated={() => {
            setCarouselOpen(false);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}
