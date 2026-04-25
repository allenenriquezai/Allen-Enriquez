"use client";

import * as React from "react";
import Link from "next/link";
import { format } from "date-fns";
import { EyeOff, Eye, Trash2 } from "lucide-react";

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
  hidden?: number | null;
  variant_label?: string | null;
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

export function AssetTile({
  asset,
  onChange,
}: {
  asset: Asset;
  onChange?: () => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const platformStatus = React.useMemo(() => {
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
  const isHidden = !!asset.hidden;

  async function toggleHidden(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      await fetch(`/api/library/${asset.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ hidden: isHidden ? 0 : 1 }),
      });
      onChange?.();
    } finally {
      setBusy(false);
    }
  }

  async function doDelete(deleteR2: boolean) {
    if (busy) return;
    setBusy(true);
    try {
      await fetch(`/api/library/${asset.id}?r2=${deleteR2 ? 1 : 0}`, {
        method: "DELETE",
      });
      onChange?.();
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  }

  return (
    <div className="relative group">
      <Link
        href={`/library/${asset.id}`}
        className={`block rounded-lg border border-border bg-card overflow-hidden flex flex-col hover:border-[var(--brand)]/60 transition-colors ${
          isHidden ? "opacity-50" : ""
        }`}
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
          {asset.variant_label && (
            <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-black/70 text-white/80 border border-white/10">
              {asset.variant_label}
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

      {/* Hover action buttons */}
      <div className={`absolute top-2 right-2 flex gap-1 transition-opacity z-10 ${busy ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
        <button
          type="button"
          onClick={toggleHidden}
          disabled={busy}
          title={isHidden ? "Unhide" : "Hide"}
          className="p-1.5 rounded bg-black/70 hover:bg-black/90 text-white/80 hover:text-white border border-white/10"
        >
          {isHidden ? <Eye className="size-3.5" /> : <EyeOff className="size-3.5" />}
        </button>
        <button
          type="button"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirmDelete(true); }}
          disabled={busy}
          title="Delete"
          className="p-1.5 rounded bg-black/70 hover:bg-red-600/90 text-white/80 hover:text-white border border-white/10"
        >
          <Trash2 className="size-3.5" />
        </button>
      </div>

      {/* Delete confirm modal */}
      {confirmDelete && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
          onClick={(e) => { e.stopPropagation(); setConfirmDelete(false); }}
        >
          <div
            className="bg-card border border-border rounded-lg p-5 max-w-sm w-full mx-4 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="font-medium">Delete asset?</div>
            <div className="text-xs text-muted-foreground">
              {asset.title ?? asset.path}
            </div>
            <div className="text-xs text-muted-foreground">
              Removes the DB row and post history. R2 deletion is optional and cannot be undone.
            </div>
            <div className="flex gap-2 justify-end pt-1">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-3 py-1.5 text-xs rounded border border-border hover:bg-muted/40"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => doDelete(false)}
                className="px-3 py-1.5 text-xs rounded border border-border hover:bg-muted/40"
              >
                DB only
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => doDelete(true)}
                className="px-3 py-1.5 text-xs rounded bg-red-600 text-white hover:bg-red-700"
              >
                DB + R2
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
