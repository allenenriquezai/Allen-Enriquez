"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { YouTubeVideoInsights } from "@/components/youtube-video-insights";
import { PostEngagementBreakdown } from "@/components/analytics/post-engagement-breakdown";
import {
  YouTubeChart,
  YouTubeTable,
  FacebookChart,
  FacebookTable,
  InstagramChart,
  InstagramTable,
  TikTokTable,
  type YtStat,
  type FbPost,
  type IgPost,
  type TtStat,
  type YtSortKey,
  type FbSortKey,
  type IgSortKey,
} from "@/components/analytics/platform-tables";

type PostsSectionProps =
  | { platform: "youtube"; stats: YtStat[]; loading: boolean; onRefresh: () => void }
  | { platform: "tiktok"; stats: TtStat[]; loading: boolean; onRefresh: () => void }
  | { platform: "instagram"; stats: IgPost[]; loading: boolean; onRefresh: () => void }
  | { platform: "facebook"; stats: FbPost[]; loading: boolean; onRefresh: () => void };

const REFRESH_LABELS: Record<string, string> = {
  youtube: "Refresh from YouTube",
  tiktok: "Refresh from TikTok",
  instagram: "Refresh from Instagram",
  facebook: "Refresh from Facebook",
};

export function PostsSection(props: PostsSectionProps) {
  const [open, setOpen] = useState(false);
  const [selectedYt, setSelectedYt] = useState<{ id: string; title: string } | null>(null);
  const [selectedOtherId, setSelectedOtherId] = useState<string | null>(null);
  const [ytSortKey, setYtSortKey] = useState<YtSortKey>("published_at");
  const [ytSortDir, setYtSortDir] = useState<"asc" | "desc">("desc");
  const [fbSortKey, setFbSortKey] = useState<FbSortKey>("created_time");
  const [fbSortDir, setFbSortDir] = useState<"asc" | "desc">("desc");
  const [igSortKey, setIgSortKey] = useState<IgSortKey>("timestamp");
  const [igSortDir, setIgSortDir] = useState<"asc" | "desc">("desc");

  const count = props.stats.length;
  const refreshLabel = props.loading
    ? "Refreshing…"
    : REFRESH_LABELS[props.platform];

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-2">
        <button
          className="flex items-center gap-2 text-sm font-medium text-foreground/70 hover:text-foreground transition-colors"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="text-xs">{open ? "▼" : "▶"}</span>
          <span>Posts{count > 0 ? ` (${count})` : ""}</span>
        </button>
        <Button
          size="sm"
          variant="outline"
          disabled={props.loading}
          onClick={() => props.onRefresh()}
        >
          {refreshLabel}
        </Button>
      </div>

      {open && (
        <div className="mt-3">
          {props.platform === "youtube" && (
            <>
              <YouTubeChart stats={props.stats} />
              <div className="mt-4">
                <YouTubeTable
                  stats={props.stats}
                  sortKey={ytSortKey}
                  sortDir={ytSortDir}
                  onSort={(key) => {
                    if (key === ytSortKey) setYtSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    else { setYtSortKey(key); setYtSortDir("desc"); }
                  }}
                  onSelect={(v) =>
                    setSelectedYt(
                      selectedYt?.id === v.video_id
                        ? null
                        : { id: v.video_id, title: v.title },
                    )
                  }
                  selectedId={selectedYt?.id ?? null}
                />
              </div>
              {selectedYt && (
                <div className="mt-4">
                  <YouTubeVideoInsights
                    videoId={selectedYt.id}
                    title={selectedYt.title}
                    onClose={() => setSelectedYt(null)}
                  />
                </div>
              )}
            </>
          )}

          {props.platform === "tiktok" && (
            <>
              <TikTokTable
                stats={props.stats}
                onSelect={(v) =>
                  setSelectedOtherId(
                    selectedOtherId === v.video_id ? null : v.video_id,
                  )
                }
                selectedId={selectedOtherId}
              />
              {selectedOtherId && (() => {
                const post = (props.stats as TtStat[]).find(
                  (v) => v.video_id === selectedOtherId,
                );
                return post ? (
                  <PostEngagementBreakdown
                    data={{ platform: "tiktok", post }}
                    onClose={() => setSelectedOtherId(null)}
                  />
                ) : null;
              })()}
            </>
          )}

          {props.platform === "instagram" && (
            <>
              <InstagramChart posts={props.stats} />
              <div className="mt-4">
                <InstagramTable
                  posts={props.stats}
                  sortKey={igSortKey}
                  sortDir={igSortDir}
                  onSort={(key) => {
                    if (key === igSortKey) setIgSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    else { setIgSortKey(key); setIgSortDir("desc"); }
                  }}
                  onSelect={(p) =>
                    setSelectedOtherId(
                      selectedOtherId === p.post_id ? null : p.post_id,
                    )
                  }
                  selectedId={selectedOtherId}
                />
              </div>
              {selectedOtherId && (() => {
                const post = (props.stats as IgPost[]).find(
                  (p) => p.post_id === selectedOtherId,
                );
                return post ? (
                  <PostEngagementBreakdown
                    data={{ platform: "instagram", post }}
                    onClose={() => setSelectedOtherId(null)}
                  />
                ) : null;
              })()}
            </>
          )}

          {props.platform === "facebook" && (
            <>
              <FacebookChart posts={props.stats} />
              <div className="mt-4">
                <FacebookTable
                  posts={props.stats}
                  sortKey={fbSortKey}
                  sortDir={fbSortDir}
                  onSort={(key) => {
                    if (key === fbSortKey) setFbSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    else { setFbSortKey(key); setFbSortDir("desc"); }
                  }}
                  onSelect={(p) =>
                    setSelectedOtherId(
                      selectedOtherId === p.post_id ? null : p.post_id,
                    )
                  }
                  selectedId={selectedOtherId}
                />
              </div>
              {selectedOtherId && (() => {
                const post = (props.stats as FbPost[]).find(
                  (p) => p.post_id === selectedOtherId,
                );
                return post ? (
                  <PostEngagementBreakdown
                    data={{ platform: "facebook", post }}
                    onClose={() => setSelectedOtherId(null)}
                  />
                ) : null;
              })()}
            </>
          )}
        </div>
      )}
    </div>
  );
}
