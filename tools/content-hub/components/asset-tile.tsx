"use client";

import * as React from "react";
import { format } from "date-fns";
import { Film, Image as ImageIcon, Check } from "lucide-react";
import { cn } from "@/lib/utils";

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
  created_at: string;
  posts: AssetPost[];
};

const PLATFORMS: Array<{ key: string; label: string }> = [
  { key: "facebook", label: "FB" },
  { key: "instagram", label: "IG" },
  { key: "tiktok", label: "TT" },
  { key: "youtube", label: "YT" },
  { key: "x", label: "X" },
];

function PlatformToggle({
  assetId,
  platform,
  label,
  post,
  onChange,
}: {
  assetId: number;
  platform: string;
  label: string;
  post: AssetPost | undefined;
  onChange: (post: AssetPost | undefined) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const checked = !!post;

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (checked) {
        const res = await fetch(
          `/api/posts?asset_id=${assetId}&platform=${platform}`,
          { method: "DELETE" },
        );
        if (res.ok) onChange(undefined);
      } else {
        const res = await fetch("/api/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ asset_id: assetId, platform }),
        });
        if (res.ok) {
          const data = await res.json();
          onChange(data.post);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      className={cn(
        "flex flex-col items-center gap-0.5 px-1.5 py-1 rounded border text-[10px] font-mono uppercase transition-colors",
        checked
          ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
          : "bg-muted/40 border-border text-muted-foreground hover:bg-muted",
      )}
    >
      <div className="flex items-center gap-1">
        {checked && <Check className="size-3" />}
        <span>{label}</span>
      </div>
      {post?.posted_at && (
        <span className="text-[9px] opacity-75">
          {format(new Date(post.posted_at), "MMM d")}
        </span>
      )}
    </button>
  );
}

export function AssetTile({ asset: initial }: { asset: Asset }) {
  const [asset, setAsset] = React.useState<Asset>(initial);
  const postByPlatform = React.useMemo(() => {
    const m = new Map<string, AssetPost>();
    for (const p of asset.posts) {
      if (!m.has(p.platform)) m.set(p.platform, p);
    }
    return m;
  }, [asset.posts]);

  const onPlatformChange = (platform: string, post: AssetPost | undefined) => {
    setAsset((prev) => {
      const filtered = prev.posts.filter((p) => p.platform !== platform);
      return post ? { ...prev, posts: [post, ...filtered] } : { ...prev, posts: filtered };
    });
  };

  const isCarousel = asset.type === "carousel";
  const Icon = isCarousel ? ImageIcon : Film;

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden flex flex-col">
      <div
        className="aspect-[9/16] flex items-center justify-center text-muted-foreground"
        style={{
          background:
            "linear-gradient(135deg, rgba(2,179,233,0.12), rgba(2,179,233,0.02))",
        }}
      >
        <Icon className="size-10 opacity-60" />
      </div>
      <div className="p-3 flex flex-col gap-2 flex-1">
        <div
          className="text-sm font-medium truncate"
          title={asset.title ?? asset.path}
        >
          {asset.title ?? "Untitled"}
        </div>
        <div className="text-[10px] text-muted-foreground font-mono">
          {format(new Date(asset.created_at), "MMM d, yyyy")}
        </div>
        <div className="flex gap-1 mt-auto pt-1">
          {PLATFORMS.map((p) => (
            <PlatformToggle
              key={p.key}
              assetId={asset.id}
              platform={p.key}
              label={p.label}
              post={postByPlatform.get(p.key)}
              onChange={(post) => onPlatformChange(p.key, post)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
