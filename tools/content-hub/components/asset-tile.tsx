"use client";

import * as React from "react";
import Link from "next/link";
import { format } from "date-fns";

export type AssetPost = {
  id: number;
  asset_id: number;
  platform: string;
  posted_at: string | null;
  url: string | null;
  status?: string | null;
  error_detail?: string | null;
  attempts?: number | null;
};

export type Asset = {
  id: number;
  path: string;
  type: string;
  title: string | null;
  url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  idea_id: number | null;
  created_at: string;
  posts: AssetPost[];
};

const PLATFORM_LABELS: Record<string, string> = {
  facebook: "FB",
  instagram: "IG",
  tiktok: "TT",
  youtube: "YT",
  x: "X",
};

function formatDuration(seconds: number | null): string | null {
  if (!seconds) return null;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function AssetTile({ asset }: { asset: Asset }) {
  const platformStatus = React.useMemo(() => {
    // Posts arrive sorted by posted_at DESC — first hit per platform is the latest attempt.
    const map: Record<string, "success" | "error"> = {};
    for (const p of asset.posts) {
      if (!map[p.platform]) {
        map[p.platform] = p.status === "error" ? "error" : "success";
      }
    }
    return map;
  }, [asset.posts]);
  const postedPlatforms = React.useMemo(
    () => Object.keys(platformStatus).sort(),
    [platformStatus],
  );

  const isVideo = asset.type === "reel" || asset.type === "youtube";
  const duration = formatDuration(asset.duration_seconds);

  return (
    <Link
      href={`/library/${asset.id}`}
      className="group rounded-lg border border-border bg-card overflow-hidden flex flex-col hover:border-[var(--brand)]/60 transition-colors"
    >
      {/* Media preview */}
      <div className="aspect-[9/16] overflow-hidden bg-muted/20 relative">
        {asset.thumbnail_url ? (
          <img src={asset.thumbnail_url} alt={asset.title ?? ""} className="w-full h-full object-cover" loading="lazy" />
        ) : asset.type === "carousel" && asset.url ? (
          <img src={asset.url} alt={asset.title ?? ""} className="w-full h-full object-cover" loading="lazy" />
        ) : isVideo && asset.url ? (
          <video src={asset.url} preload="metadata" muted playsInline className="w-full h-full object-cover" />
        ) : (
          <div
            className="w-full h-full flex items-center justify-center text-muted-foreground"
            style={{ background: "linear-gradient(135deg, rgba(2,179,233,0.12), rgba(2,179,233,0.02))" }}
          >
            <span className="text-[10px] font-mono">No preview</span>
          </div>
        )}
        {duration && (
          <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono bg-black/70 text-white">
            {duration}
          </span>
        )}
      </div>

      <div className="p-3 flex flex-col gap-2 flex-1">
        <div className="text-sm font-medium truncate" title={asset.title ?? asset.path}>
          {asset.title ?? "Untitled"}
        </div>
        <div className="text-[10px] text-muted-foreground font-mono">
          {format(new Date(asset.created_at), "MMM d, yyyy")}
        </div>

        {postedPlatforms.length > 0 && (
          <div className="flex gap-1 flex-wrap mt-auto pt-1">
            {postedPlatforms.map((platform) => {
              const failed = platformStatus[platform] === "error";
              const cls = failed
                ? "bg-red-500/15 text-red-400 border-red-500/40"
                : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
              return (
                <span
                  key={platform}
                  title={failed ? "Last publish failed — open to retry" : "Posted"}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border ${cls}`}
                >
                  {PLATFORM_LABELS[platform] || platform.slice(0, 2).toUpperCase()}
                  {failed && " ⚠"}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </Link>
  );
}
