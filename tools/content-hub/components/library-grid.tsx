"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { AssetTile, type Asset } from "@/components/asset-tile";

export function LibraryGrid({ assets }: { assets: Asset[] }) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState<"all" | "reels" | "carousels" | "images">("all");
  const [sortOrder, setSortOrder] = React.useState<"newest" | "oldest" | "unposted">("newest");

  const filtered = React.useMemo(() => {
    let result = assets;

    // Apply search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((a) =>
        a.title?.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
      );
    }

    // Apply type filter
    if (typeFilter === "reels") {
      result = result.filter((a) => a.type === "reel" || a.type === "youtube");
    } else if (typeFilter === "carousels") {
      result = result.filter((a) => a.type === "carousel");
    } else if (typeFilter === "images") {
      result = result.filter((a) => a.type === "image");
    }

    // Apply sort
    if (sortOrder === "newest") {
      result = result.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } else if (sortOrder === "oldest") {
      result = result.sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    } else if (sortOrder === "unposted") {
      result = result.sort((a, b) => {
        const aUnposted = a.posts.length === 0 ? 0 : 1;
        const bUnposted = b.posts.length === 0 ? 0 : 1;
        if (aUnposted !== bUnposted) return aUnposted - bUnposted;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
    }

    return result;
  }, [assets, searchQuery, typeFilter, sortOrder]);

  const videos = filtered.filter((a) => a.type === "reel" || a.type === "youtube");
  const carousels = filtered.filter((a) => a.type === "carousel");

  return (
    <div className="space-y-6">
      {/* Filters & Sort */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        {/* Search */}
        <div className="flex-1">
          <label className="block text-xs font-mono uppercase text-muted-foreground mb-2">
            Search
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter by title or filename…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
            />
          </div>
        </div>

        {/* Type Filter */}
        <div>
          <label className="block text-xs font-mono uppercase text-muted-foreground mb-2">
            Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
            className="px-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
          >
            <option value="all">All</option>
            <option value="reels">Reels & YouTube</option>
            <option value="carousels">Carousels</option>
            <option value="images">Images</option>
          </select>
        </div>

        {/* Sort */}
        <div>
          <label className="block text-xs font-mono uppercase text-muted-foreground mb-2">
            Sort
          </label>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}
            className="px-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="unposted">Unposted First</option>
          </select>
        </div>
      </div>

      {/* Grid sections */}
      {filtered.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-sm text-muted-foreground">
            {searchQuery || typeFilter !== "all" ? "No assets match your filters." : "No assets yet."}
          </p>
        </div>
      ) : (
        <>
          {videos.length > 0 && (
            <section>
              <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">
                Videos ({videos.length})
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {videos.map((a) => (
                  <AssetTile key={a.id} asset={a} />
                ))}
              </div>
            </section>
          )}

          {carousels.length > 0 && (
            <section>
              <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">
                Carousels ({carousels.length})
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {carousels.map((a) => (
                  <AssetTile key={a.id} asset={a} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
