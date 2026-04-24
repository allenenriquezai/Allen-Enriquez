"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { X, Check, Loader2 } from "lucide-react";

type PlatformStatus = "idle" | "loading" | "success" | "error";

interface Asset {
  id: number;
  url: string;
  title: string | null;
  type: string;
  idea_id?: number | null;
}

interface QuickPublishModalProps {
  asset: Asset;
  scheduleId?: number;
  captions?: Record<string, string>;
  onClose: () => void;
}

const PLATFORMS = [
  { key: "fb", label: "Facebook", color: "#1877F2", captionKey: "caption_ig" },
  { key: "ig", label: "Instagram", color: "#E1306C", captionKey: "caption_ig" },
  { key: "yt", label: "YouTube", color: "#FF0000", captionKey: "caption_yt" },
  { key: "tiktok", label: "TikTok", color: "#010101", captionKey: "caption_tiktok" },
];

export function QuickPublishModal({ asset, scheduleId, captions: propCaptions, onClose }: QuickPublishModalProps) {
  const router = useRouter();
  const [selected, setSelected] = React.useState<Set<string>>(new Set(["fb", "ig"]));
  const [captions, setCaptions] = React.useState<Record<string, string>>(propCaptions ?? {});
  const [scheduleMode, setScheduleMode] = React.useState(false);
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [status, setStatus] = React.useState<Record<string, PlatformStatus>>({});
  const [done, setDone] = React.useState(false);
  const [loadingCaptions, setLoadingCaptions] = React.useState(false);

  React.useEffect(() => {
    if (!asset.idea_id || propCaptions) return;
    setLoadingCaptions(true);
    fetch(`/api/scripts?idea_id=${asset.idea_id}`)
      .then((r) => r.json())
      .then((data) => {
        const map: Record<string, string> = {};
        for (const s of data.scripts ?? []) {
          if (s.variant?.startsWith("caption_")) map[s.variant] = s.body;
        }
        setCaptions(map);
      })
      .finally(() => setLoadingCaptions(false));
  }, [asset.idea_id, propCaptions]);

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const publish = async () => {
    const platforms = [...selected];
    platforms.forEach((p) => setStatus((s) => ({ ...s, [p]: "loading" })));

    const when = scheduleMode && scheduledAt ? scheduledAt : undefined;

    const calls: Promise<void>[] = [];

    if (platforms.includes("fb")) {
      const caption = captions["caption_ig"] ?? "";
      calls.push(
        fetch("/api/facebook/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: caption, scheduled_at: when }),
        })
          .then((r) => {
            setStatus((s) => ({ ...s, fb: r.ok ? "success" : "error" }));
            if (r.ok) logPost("facebook");
          })
          .catch(() => setStatus((s) => ({ ...s, fb: "error" }))),
      );
    }

    if (platforms.includes("ig")) {
      const caption = captions["caption_ig"] ?? "";
      calls.push(
        fetch("/api/instagram/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ caption, media_url: asset.url, media_type: "REELS", scheduled_at: when }),
        })
          .then((r) => {
            setStatus((s) => ({ ...s, ig: r.ok ? "success" : "error" }));
            if (r.ok) logPost("instagram");
          })
          .catch(() => setStatus((s) => ({ ...s, ig: "error" }))),
      );
    }

    if (platforms.includes("yt")) {
      const description = captions["caption_yt"] ?? "";
      calls.push(
        fetch("/api/youtube/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: asset.title ?? "Untitled",
            description,
            media_url: asset.url,
            schedule_id: scheduleId,
            scheduled_at: when,
          }),
        })
          .then((r) => {
            setStatus((s) => ({ ...s, yt: r.ok ? "success" : "error" }));
            if (r.ok) logPost("youtube");
          })
          .catch(() => setStatus((s) => ({ ...s, yt: "error" }))),
      );
    }

    if (platforms.includes("tiktok")) {
      const description = captions["caption_tiktok"] ?? "";
      calls.push(
        fetch("/api/tiktok/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: asset.title ?? "Untitled",
            description,
            media_url: asset.url,
            schedule_id: scheduleId,
            scheduled_at: when,
          }),
        })
          .then((r) => {
            setStatus((s) => ({ ...s, tiktok: r.ok ? "success" : "error" }));
            if (r.ok) logPost("tiktok");
          })
          .catch(() => setStatus((s) => ({ ...s, tiktok: "error" }))),
      );
    }

    await Promise.allSettled(calls);

    if (scheduleId) {
      await fetch(`/api/schedule/${scheduleId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "posted" }),
      });
    }

    setDone(true);
    router.refresh();
  };

  const logPost = (platform: string) => {
    fetch("/api/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_id: asset.id, platform, url: asset.url }),
    }).catch(() => {});
  };

  const isPublishing = Object.values(status).some((s) => s === "loading");
  const canPublish = selected.size > 0 && !isPublishing && !done;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        className="w-full max-w-lg rounded-xl border border-border bg-background shadow-xl flex flex-col gap-5 p-6"
        style={{ maxHeight: "90vh", overflowY: "auto" }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold">Quick Publish</h2>
            <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-xs">
              {asset.title ?? "Untitled"}
            </p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground mt-0.5">
            <X className="size-4" />
          </button>
        </div>

        {/* Asset URL */}
        <div className="rounded-lg bg-muted/20 border border-border/40 px-3 py-2">
          <p className="text-[10px] font-mono uppercase text-muted-foreground mb-1">Video URL</p>
          <p className="text-xs font-mono truncate text-foreground/80">{asset.url}</p>
        </div>

        {/* Platform selection */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Platforms
          </p>
          <div className="flex gap-2 flex-wrap">
            {PLATFORMS.map((p) => {
              const st = status[p.key];
              const isOn = selected.has(p.key);
              return (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => !isPublishing && !done && toggle(p.key)}
                  disabled={isPublishing || done}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all"
                  style={
                    isOn
                      ? { borderColor: p.color, color: p.color, background: `${p.color}18` }
                      : { borderColor: "var(--border)", color: "var(--muted-foreground)" }
                  }
                >
                  {st === "loading" && <Loader2 className="size-3 animate-spin" />}
                  {st === "success" && <Check className="size-3" style={{ color: "#22c55e" }} />}
                  {st === "error" && <X className="size-3 text-red-400" />}
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Captions */}
        {loadingCaptions ? (
          <p className="text-xs text-muted-foreground">Loading captions…</p>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Captions
            </p>
            {[
              { label: "IG / FB caption", key: "caption_ig" },
              { label: "YouTube description", key: "caption_yt" },
              { label: "TikTok caption", key: "caption_tiktok" },
            ].map(({ label, key }) => (
              <div key={key}>
                <p className="text-[10px] font-mono uppercase text-muted-foreground mb-1">{label}</p>
                <textarea
                  rows={3}
                  value={captions[key] ?? ""}
                  onChange={(e) => setCaptions((prev) => ({ ...prev, [key]: e.target.value }))}
                  placeholder="No caption yet — type here or generate from Scripts"
                  className="w-full text-xs bg-muted/10 border border-border/40 rounded-lg p-3 resize-none font-sans leading-relaxed focus:outline-none focus:border-border"
                />
              </div>
            ))}
          </div>
        )}

        {/* Schedule */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Timing
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setScheduleMode(false)}
              className="px-3 py-1.5 rounded-full text-xs border transition-all"
              style={
                !scheduleMode
                  ? { borderColor: "var(--brand)", color: "var(--brand)", background: "rgba(2,179,233,0.1)" }
                  : { borderColor: "var(--border)", color: "var(--muted-foreground)" }
              }
            >
              Post now
            </button>
            <button
              type="button"
              onClick={() => setScheduleMode(true)}
              className="px-3 py-1.5 rounded-full text-xs border transition-all"
              style={
                scheduleMode
                  ? { borderColor: "var(--brand)", color: "var(--brand)", background: "rgba(2,179,233,0.1)" }
                  : { borderColor: "var(--border)", color: "var(--muted-foreground)" }
              }
            >
              Schedule
            </button>
          </div>
          {scheduleMode && (
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="mt-2 text-xs bg-transparent border border-border/60 rounded px-2 py-1.5"
            />
          )}
        </div>

        {/* Status summary */}
        {done && (
          <p className="text-xs text-emerald-400 font-medium">
            Done! Check each platform for the live posts.
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/40">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
            {done ? "Close" : "Cancel"}
          </Button>
          {!done && (
            <Button
              size="sm"
              disabled={!canPublish}
              onClick={publish}
              className="text-xs gap-1.5"
            >
              {isPublishing ? (
                <>
                  <Loader2 className="size-3 animate-spin" />
                  Publishing…
                </>
              ) : (
                `Publish to ${selected.size} platform${selected.size !== 1 ? "s" : ""}`
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
