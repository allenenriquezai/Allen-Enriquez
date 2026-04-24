"use client";

import * as React from "react";
import { format } from "date-fns";
import { Send } from "lucide-react";
import { QuickPublishModal } from "@/components/quick-publish-modal";

export type AssetPost = {
  id: number;
  asset_id: number;
  platform: string;
  posted_at: string | null;
  url: string | null;
};

export type Asset = {
  id: number;
  path: string;
  type: string;
  title: string | null;
  url: string | null;
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

export function AssetTile({ asset: initial }: { asset: Asset }) {
  const [showPublish, setShowPublish] = React.useState(false);

  const postedPlatforms = React.useMemo(() => {
    const platforms = new Set<string>();
    for (const p of initial.posts) {
      platforms.add(p.platform);
    }
    return Array.from(platforms).sort();
  }, [initial.posts]);

  return (
    <>
      {showPublish && initial.url && (
        <QuickPublishModal
          asset={{ id: initial.id, url: initial.url, title: initial.title, type: initial.type, idea_id: initial.idea_id }}
          onClose={() => setShowPublish(false)}
        />
      )}
      <div className="rounded-lg border border-border bg-card overflow-hidden flex flex-col">
        {/* Media preview or gradient fallback */}
        <div className="aspect-[9/16] overflow-hidden">
          {initial.type === "carousel" && initial.url ? (
            <img
              src={initial.url}
              alt={initial.title ?? ""}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (initial.type === "reel" || initial.type === "youtube") && initial.url ? (
            <video
              src={initial.url}
              preload="metadata"
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          ) : (
            <div
              className="w-full h-full flex items-center justify-center text-muted-foreground"
              style={{
                background:
                  "linear-gradient(135deg, rgba(2,179,233,0.12), rgba(2,179,233,0.02))",
              }}
            >
              <span className="text-[10px] font-mono">No preview</span>
            </div>
          )}
        </div>

        {/* Title and metadata */}
        <div className="p-3 flex flex-col gap-2 flex-1">
          <div
            className="text-sm font-medium truncate"
            title={initial.title ?? initial.path}
          >
            {initial.title ?? "Untitled"}
          </div>
          <div className="text-[10px] text-muted-foreground font-mono">
            {format(new Date(initial.created_at), "MMM d, yyyy")}
          </div>

          {/* Posted-to chips */}
          {postedPlatforms.length > 0 && (
            <div className="flex gap-1 flex-wrap mt-auto pt-1">
              {postedPlatforms.map((platform) => (
                <span
                  key={platform}
                  className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                >
                  {PLATFORM_LABELS[platform] || platform.slice(0, 2).toUpperCase()}
                </span>
              ))}
            </div>
          )}

          {/* Post CTA button */}
          {initial.url ? (
            <button
              type="button"
              onClick={() => setShowPublish(true)}
              className="mt-2 flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-1 rounded border transition-colors"
              style={{ color: "var(--brand)", borderColor: "rgba(2,179,233,0.3)", background: "rgba(2,179,233,0.06)" }}
            >
              <Send className="size-3" />
              Post this
            </button>
          ) : (
            <span className="mt-2 text-[10px] font-mono text-muted-foreground/50">No URL — add via Library</span>
          )}
        </div>
      </div>
    </>
  );
}
