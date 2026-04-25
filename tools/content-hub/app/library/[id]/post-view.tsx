"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, Loader2, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Asset } from "@/components/asset-tile";

type Idea = { id: number; title: string };
type Script = { id: number; idea_id: number; variant: string; body: string };

interface PostViewProps {
  asset: Asset;
  ideas: Idea[];
  initialScripts: Script[];
}

type PlatformKey = "fb" | "ig" | "yt" | "tiktok";
type PlatformStatus = "idle" | "loading" | "success" | "error";

const PLATFORMS: Array<{
  key: PlatformKey;
  label: string;
  captionKey: string;
  minMinutes: number;
}> = [
  { key: "fb", label: "Facebook", captionKey: "caption_fb", minMinutes: 10 },
  { key: "ig", label: "Instagram", captionKey: "caption_ig", minMinutes: 10 },
  { key: "yt", label: "YouTube", captionKey: "caption_yt", minMinutes: 0 },
  { key: "tiktok", label: "TikTok", captionKey: "caption_tiktok", minMinutes: 15 },
];

const CAPTION_TABS = [
  { key: "caption_fb", label: "Facebook", limit: 63206 },
  { key: "caption_ig", label: "Instagram", limit: 2200 },
  { key: "caption_yt", label: "YouTube", limit: 5000 },
  { key: "caption_tiktok", label: "TikTok", limit: 2200 },
  { key: "caption_x", label: "X", limit: 280 },
  { key: "caption_linkedin", label: "LinkedIn", limit: 3000 },
] as const;

function scriptsToCaptions(scripts: Script[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const s of scripts) {
    if (s.variant?.startsWith("caption_")) map[s.variant] = s.body;
  }
  if (!map["caption_fb"] && map["caption_ig"]) map["caption_fb"] = map["caption_ig"];
  return map;
}

export function PostView({ asset, ideas, initialScripts }: PostViewProps) {
  const router = useRouter();

  // Asset metadata (editable)
  const [title, setTitle] = React.useState(asset.title ?? "");
  const [thumbnailUrl, setThumbnailUrl] = React.useState(asset.thumbnail_url ?? "");
  const [ideaId, setIdeaId] = React.useState<number | null>(asset.idea_id ?? null);
  const [metaDirty, setMetaDirty] = React.useState(false);
  const [savingMeta, setSavingMeta] = React.useState(false);
  const [metaSavedAt, setMetaSavedAt] = React.useState<number | null>(null);
  const [uploadingThumb, setUploadingThumb] = React.useState(false);
  const thumbFileRef = React.useRef<HTMLInputElement>(null);

  // Captions
  const [captions, setCaptions] = React.useState<Record<string, string>>(
    scriptsToCaptions(initialScripts),
  );
  const captionBaseline = React.useRef<Record<string, string>>(scriptsToCaptions(initialScripts));
  const [activeCaption, setActiveCaption] = React.useState<string>("caption_ig");
  const [loadingCaptions, setLoadingCaptions] = React.useState(false);
  const [savingScript, setSavingScript] = React.useState(false);
  const [scriptSavedAt, setScriptSavedAt] = React.useState<number | null>(null);
  const [captionDirty, setCaptionDirty] = React.useState<Record<string, boolean>>({});
  const [syndicating, setSyndicating] = React.useState(false);
  const [syndicateError, setSyndicateError] = React.useState<string | null>(null);

  // Publish controls — preselect platforms whose latest publish attempt failed; else default IG.
  const initialSelected = React.useMemo<Set<PlatformKey>>(() => {
    const platformToKey: Record<string, PlatformKey> = {
      facebook: "fb",
      instagram: "ig",
      youtube: "yt",
      tiktok: "tiktok",
    };
    const latestByPlatform: Record<string, string> = {};
    for (const p of asset.posts ?? []) {
      if (!latestByPlatform[p.platform]) latestByPlatform[p.platform] = p.status ?? "success";
    }
    const failed = new Set<PlatformKey>();
    for (const [name, st] of Object.entries(latestByPlatform)) {
      if (st === "error" && platformToKey[name]) failed.add(platformToKey[name]);
    }
    return failed.size > 0 ? failed : new Set<PlatformKey>(["ig"]);
  }, [asset.posts]);
  const [selected, setSelected] = React.useState<Set<PlatformKey>>(initialSelected);
  const hasRetryQueue = initialSelected.size > 0 && (asset.posts ?? []).some((p) => p.status === "error");
  const [scheduleMode, setScheduleMode] = React.useState(false);
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [status, setStatus] = React.useState<Record<PlatformKey, PlatformStatus>>({
    fb: "idle",
    ig: "idle",
    yt: "idle",
    tiktok: "idle",
  });
  const [scheduleError, setScheduleError] = React.useState<string | null>(null);
  const [publishErrors, setPublishErrors] = React.useState<Record<string, string>>({});
  const [done, setDone] = React.useState(false);

  const isVideo = asset.type === "reel" || asset.type === "youtube";

  // When idea changes, reload captions and reset baseline
  React.useEffect(() => {
    if (ideaId === asset.idea_id) return;
    if (!ideaId) {
      setCaptions({});
      captionBaseline.current = {};
      setCaptionDirty({});
      return;
    }
    setLoadingCaptions(true);
    fetch(`/api/scripts?idea_id=${ideaId}`)
      .then((r) => r.json())
      .then((data) => {
        const next = scriptsToCaptions(data.scripts ?? []);
        setCaptions(next);
        captionBaseline.current = next;
        setCaptionDirty({});
      })
      .finally(() => setLoadingCaptions(false));
  }, [ideaId, asset.idea_id]);

  // Debounced autosave for asset metadata (title, thumbnail, idea_id)
  React.useEffect(() => {
    if (!metaDirty) return;
    const t = setTimeout(async () => {
      setSavingMeta(true);
      try {
        const res = await fetch("/api/library", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: asset.id,
            title: title.trim() || null,
            thumbnail_url: thumbnailUrl.trim() || null,
            idea_id: ideaId,
          }),
        });
        if (res.ok) {
          setMetaDirty(false);
          setMetaSavedAt(Date.now());
        }
      } finally {
        setSavingMeta(false);
      }
    }, 800);
    return () => clearTimeout(t);
  }, [metaDirty, title, thumbnailUrl, ideaId, asset.id]);

  // Debounced autosave for active caption
  const activeValueForEffect = captions[activeCaption] ?? "";
  React.useEffect(() => {
    if (!ideaId) return;
    if (!captionDirty[activeCaption]) return;
    const t = setTimeout(async () => {
      setSavingScript(true);
      try {
        const res = await fetch("/api/scripts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idea_id: ideaId, variant: activeCaption, body: activeValueForEffect }),
        });
        if (res.ok) {
          setScriptSavedAt(Date.now());
          captionBaseline.current = { ...captionBaseline.current, [activeCaption]: activeValueForEffect };
          setCaptionDirty((d) => ({ ...d, [activeCaption]: false }));
        }
      } finally {
        setSavingScript(false);
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [activeValueForEffect, activeCaption, ideaId, captionDirty]);

  const togglePlatform = (key: PlatformKey) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const uploadThumb = async (file: File) => {
    setUploadingThumb(true);
    try {
      const presignRes = await fetch("/api/upload/presigned", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, contentType: file.type }),
      });
      if (!presignRes.ok) throw new Error("presign failed");
      const { uploadUrl, publicUrl } = await presignRes.json();
      const putRes = await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
      if (!putRes.ok) throw new Error("upload failed");
      setThumbnailUrl(publicUrl);
      setMetaDirty(true);
    } catch (e) {
      console.warn("Thumbnail upload failed:", e);
    } finally {
      setUploadingThumb(false);
      if (thumbFileRef.current) thumbFileRef.current.value = "";
    }
  };

  const validateSchedule = (): string | null => {
    if (!scheduleMode || !scheduledAt) return null;
    const when = new Date(scheduledAt).getTime();
    const now = Date.now();
    if (when <= now) return "Scheduled time must be in the future.";
    for (const key of selected) {
      const platform = PLATFORMS.find((p) => p.key === key);
      if (platform && when - now < platform.minMinutes * 60 * 1000) {
        return `${platform.label} requires scheduling ≥${platform.minMinutes} min in the future.`;
      }
    }
    return null;
  };

  const logPost = (
    platform: string,
    status: "success" | "error" = "success",
    error_detail: string | null = null,
    platform_post_id: string | null = null,
    platform_meta: Record<string, unknown> | null = null,
  ) => {
    fetch("/api/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_id: asset.id,
        platform,
        url: asset.url,
        status,
        error_detail,
        platform_post_id,
        platform_meta,
      }),
    }).catch(() => {});
  };

  const syndicateCaptions = async () => {
    const sourceBody = (captions[activeCaption] ?? "").trim();
    if (!ideaId || !sourceBody || syndicating) return;
    setSyndicating(true);
    setSyndicateError(null);
    try {
      const res = await fetch(`/api/library/${asset.id}/syndicate-captions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sourceVariant: activeCaption, sourceBody, ideaId }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setSyndicateError(j.error || `HTTP ${res.status}`);
        return;
      }
      const { captions: synth } = (await res.json()) as { captions: Record<string, string> };
      setCaptions((prev) => ({ ...prev, ...synth }));
      captionBaseline.current = { ...captionBaseline.current, ...synth };
      setCaptionDirty((d) => {
        const next = { ...d };
        for (const k of Object.keys(synth)) next[k] = false;
        return next;
      });
      setScriptSavedAt(Date.now());
    } catch (e) {
      setSyndicateError(String(e));
    } finally {
      setSyndicating(false);
    }
  };

  const publish = async () => {
    const err = validateSchedule();
    if (err) {
      setScheduleError(err);
      return;
    }
    setScheduleError(null);
    setPublishErrors({});
    if (!asset.url) {
      setScheduleError("Asset has no media URL. Upload or paste a URL first.");
      return;
    }

    const chosen = [...selected];
    chosen.forEach((p) => setStatus((s) => ({ ...s, [p]: "loading" })));
    const when = scheduleMode && scheduledAt ? scheduledAt : undefined;

    const PLATFORM_NAMES: Record<PlatformKey, string> = {
      fb: "facebook",
      ig: "instagram",
      yt: "youtube",
      tiktok: "tiktok",
    };
    const recordError = async (key: PlatformKey, r: Response) => {
      let detail = `HTTP ${r.status}`;
      try {
        const j = await r.json();
        detail = j.detail || j.error || JSON.stringify(j);
        if (typeof detail !== "string") detail = JSON.stringify(detail);
      } catch {}
      const trimmed = detail.slice(0, 300);
      setPublishErrors((e) => ({ ...e, [key]: trimmed }));
      logPost(PLATFORM_NAMES[key], "error", trimmed);
    };
    const recordNetworkError = (key: PlatformKey, e: unknown) => {
      const detail = String(e).slice(0, 300);
      setPublishErrors((er) => ({ ...er, [key]: detail }));
      logPost(PLATFORM_NAMES[key], "error", detail);
    };

    const calls: Promise<void>[] = [];

    type PlatformId = { id: string | null; meta: Record<string, unknown> | null };
    const extractIds: Record<PlatformKey, (j: Record<string, unknown>) => PlatformId> = {
      // FB returns { ok: true, result: { id: 'pageid_postid' } }
      fb: (j) => {
        const result = j.result as Record<string, unknown> | undefined;
        return { id: (result?.id as string) ?? (j.post_id as string) ?? (j.id as string) ?? null, meta: j };
      },
      // IG returns post_id (the published media id)
      ig: (j) => ({ id: (j.post_id as string) ?? (j.id as string) ?? null, meta: j }),
      // YT returns video_id
      yt: (j) => ({ id: (j.video_id as string) ?? (j.id as string) ?? null, meta: j }),
      // TikTok returns video_id (post_id) once published
      tiktok: (j) => ({ id: (j.video_id as string) ?? (j.publish_id as string) ?? (j.id as string) ?? null, meta: j }),
    };
    const handleSuccess = async (key: PlatformKey, r: Response) => {
      let json: Record<string, unknown> = {};
      try { json = await r.json(); } catch {}
      const { id, meta } = extractIds[key](json);
      logPost(PLATFORM_NAMES[key], "success", null, id, meta);
    };

    if (chosen.includes("fb")) {
      const caption = captions["caption_fb"] || captions["caption_ig"] || "";
      calls.push(
        fetch("/api/facebook/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: caption,
            media_url: asset.url,
            media_type: isVideo ? "video" : "image",
            scheduled_at: when,
          }),
        })
          .then(async (r) => {
            setStatus((s) => ({ ...s, fb: r.ok ? "success" : "error" }));
            if (r.ok) await handleSuccess("fb", r);
            else await recordError("fb", r);
          })
          .catch((e) => {
            setStatus((s) => ({ ...s, fb: "error" }));
            recordNetworkError("fb", e);
          }),
      );
    }
    if (chosen.includes("ig")) {
      const caption = captions["caption_ig"] ?? "";
      calls.push(
        fetch("/api/instagram/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ caption, media_url: asset.url, media_type: "REELS", scheduled_at: when }),
        })
          .then(async (r) => {
            setStatus((s) => ({ ...s, ig: r.ok ? "success" : "error" }));
            if (r.ok) await handleSuccess("ig", r);
            else await recordError("ig", r);
          })
          .catch((e) => {
            setStatus((s) => ({ ...s, ig: "error" }));
            recordNetworkError("ig", e);
          }),
      );
    }
    if (chosen.includes("yt")) {
      const description = captions["caption_yt"] ?? "";
      calls.push(
        fetch("/api/youtube/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title || asset.title || "Untitled",
            description,
            media_url: asset.url,
            scheduled_at: when,
          }),
        })
          .then(async (r) => {
            setStatus((s) => ({ ...s, yt: r.ok ? "success" : "error" }));
            if (r.ok) await handleSuccess("yt", r);
            else await recordError("yt", r);
          })
          .catch((e) => {
            setStatus((s) => ({ ...s, yt: "error" }));
            recordNetworkError("yt", e);
          }),
      );
    }
    if (chosen.includes("tiktok")) {
      const description = captions["caption_tiktok"] ?? "";
      calls.push(
        fetch("/api/tiktok/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title || asset.title || "Untitled",
            description,
            media_url: asset.url,
            scheduled_at: when,
          }),
        })
          .then(async (r) => {
            setStatus((s) => ({ ...s, tiktok: r.ok ? "success" : "error" }));
            if (r.ok) await handleSuccess("tiktok", r);
            else await recordError("tiktok", r);
          })
          .catch((e) => {
            setStatus((s) => ({ ...s, tiktok: "error" }));
            recordNetworkError("tiktok", e);
          }),
      );
    }

    await Promise.allSettled(calls);
    setStatus((cur) => {
      const allOk = chosen.every((p) => cur[p] === "success");
      if (allOk) setDone(true);
      return cur;
    });
    router.refresh();
  };

  const isPublishing = Object.values(status).some((s) => s === "loading");
  const canPublish = selected.size > 0 && !isPublishing && !done && !!asset.url;
  const activeCaptionTab = CAPTION_TABS.find((t) => t.key === activeCaption)!;
  const activeValue = captions[activeCaption] ?? "";
  const overLimit = activeValue.length > activeCaptionTab.limit;

  return (
    <div className="pb-32">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <Link
          href="/library"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Library
        </Link>
        <div className="flex items-center gap-2 text-[11px] font-mono">
          {savingMeta ? (
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Loader2 className="size-3 animate-spin" /> Saving…
            </span>
          ) : metaDirty ? (
            <span className="text-amber-400">Unsaved</span>
          ) : metaSavedAt ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <Check className="size-3" /> Saved
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Right column on desktop: media preview only (sticky) */}
        <div className="lg:col-span-1 lg:order-2 flex flex-col gap-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-lg border border-border overflow-hidden bg-muted/20 aspect-[9/16]">
            {isVideo && asset.url ? (
              <video src={asset.url} controls className="w-full h-full object-contain" poster={thumbnailUrl || undefined} />
            ) : asset.url ? (
              <img src={thumbnailUrl || asset.url} alt={title} className="w-full h-full object-contain" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                <span className="text-sm">No media</span>
              </div>
            )}
          </div>
        </div>

        {/* Main column: Title → Post to → Thumbnail → Captions → Linked idea */}
        <div className="lg:col-span-2 lg:order-1 flex flex-col gap-5">
          {/* Title */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Title</p>
            <input
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setMetaDirty(true);
              }}
              placeholder="Give this asset a clear name"
              className="w-full text-base bg-muted/10 border border-border/40 rounded-lg px-3 py-2 focus:outline-none focus:border-border"
            />
          </div>

          {/* Platform picker */}
          <div>
            <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Post to
              </p>
              {hasRetryQueue && !done && (
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-red-500/15 text-red-400 border border-red-500/40">
                  Retry queued — last attempt failed for {[...initialSelected].join(", ")}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {PLATFORMS.map((p) => {
                const on = selected.has(p.key);
                const st = status[p.key];
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => !isPublishing && !done && togglePlatform(p.key)}
                    disabled={isPublishing || done}
                    className="flex items-center justify-center gap-2 px-3 py-3 rounded-lg text-sm font-medium border-2 transition-all"
                    style={
                      on
                        ? { borderColor: "var(--brand)", color: "var(--brand)", background: "rgba(2,179,233,0.12)" }
                        : { borderColor: "var(--border)", color: "var(--muted-foreground)" }
                    }
                  >
                    {st === "loading" ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : st === "error" ? (
                      <X className="size-4 text-red-400" />
                    ) : on ? (
                      <Check className="size-4" />
                    ) : null}
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Thumbnail */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Thumbnail</p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={thumbnailUrl}
                onChange={(e) => {
                  setThumbnailUrl(e.target.value);
                  setMetaDirty(true);
                }}
                placeholder="Paste URL or upload →"
                className="flex-1 text-xs bg-muted/10 border border-border/40 rounded-lg px-3 py-2 focus:outline-none focus:border-border font-mono"
              />
              <input
                ref={thumbFileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && uploadThumb(e.target.files[0])}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => thumbFileRef.current?.click()}
                disabled={uploadingThumb}
              >
                {uploadingThumb ? <Loader2 className="size-3 animate-spin" /> : <Upload className="size-3" />}
              </Button>
            </div>
          </div>

          {/* Caption tabs */}
          <div>
            <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Captions
              </p>
              <div className="flex items-center gap-2 text-[10px] font-mono">
                {loadingCaptions && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
                {!ideaId ? (
                  <span className="text-muted-foreground/60">
                    Link an idea to autosave captions
                  </span>
                ) : savingScript ? (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Loader2 className="size-3 animate-spin" /> Saving…
                  </span>
                ) : captionDirty[activeCaption] ? (
                  <span className="text-amber-400">Unsaved</span>
                ) : scriptSavedAt ? (
                  <span className="flex items-center gap-1 text-emerald-400">
                    <Check className="size-3" /> Saved
                  </span>
                ) : null}
              </div>
            </div>
            <div className="flex gap-1 border-b border-border mb-3 overflow-x-auto">
              {CAPTION_TABS.map((t) => {
                const active = activeCaption === t.key;
                const value = captions[t.key] ?? "";
                const hasContent = value.trim().length > 0;
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setActiveCaption(t.key)}
                    className="relative px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors"
                    style={{
                      color: active ? "var(--brand)" : hasContent ? "var(--foreground)" : "var(--muted-foreground)",
                      borderBottom: active ? "2px solid var(--brand)" : "2px solid transparent",
                      marginBottom: "-1px",
                    }}
                  >
                    {t.label}
                    {hasContent && !active && (
                      <span className="inline-block ml-1.5 size-1.5 rounded-full bg-emerald-400" />
                    )}
                  </button>
                );
              })}
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] font-mono text-muted-foreground">
                  {activeCaptionTab.label} — {activeCaption === "caption_fb" && !captions["caption_fb"] ? "falls back to IG caption if blank" : `${activeValue.length.toLocaleString()} / ${activeCaptionTab.limit.toLocaleString()}`}
                </p>
              </div>
              <textarea
                rows={4}
                value={activeValue}
                onChange={(e) => {
                  const v = e.target.value;
                  setCaptions((prev) => ({ ...prev, [activeCaption]: v }));
                  setCaptionDirty((d) => ({ ...d, [activeCaption]: v !== (captionBaseline.current[activeCaption] ?? "") }));
                  setScriptSavedAt(null);
                }}
                placeholder={`Write ${activeCaptionTab.label} caption here…`}
                className={`w-full text-sm bg-muted/10 border rounded-lg p-4 resize-none overflow-hidden [field-sizing:content] font-sans leading-relaxed focus:outline-none ${
                  overLimit ? "border-red-400/60" : "border-border/40 focus:border-border"
                }`}
              />
              <div className="flex items-center justify-between mt-2 gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={syndicateCaptions}
                  disabled={!ideaId || !activeValue.trim() || syndicating}
                  className="text-[10px] font-mono px-2 py-1 rounded border border-border/40 hover:border-brand transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  {syndicating ? (
                    <>
                      <Loader2 className="size-3 animate-spin" /> Syndicating…
                    </>
                  ) : (
                    <>Syndicate {activeCaptionTab.label} → other platforms</>
                  )}
                </button>
                {syndicateError && (
                  <span className="text-[10px] font-mono text-red-400">{syndicateError}</span>
                )}
              </div>
            </div>
          </div>

          {/* Linked idea */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Linked idea</p>
            <select
              value={ideaId ?? ""}
              onChange={(e) => {
                setIdeaId(e.target.value ? parseInt(e.target.value, 10) : null);
                setMetaDirty(true);
              }}
              className="w-full text-sm bg-muted/10 border border-border/40 rounded-lg px-3 py-2 focus:outline-none focus:border-border"
            >
              <option value="">— None —</option>
              {ideas.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-muted-foreground/60 font-mono mt-1">
              Pulls caption variants from this idea's scripts.
            </p>
          </div>
        </div>
      </div>

      {/* Sticky bottom publish bar — centered */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur z-40">
        <div className="max-w-7xl mx-auto px-6 py-3 flex flex-wrap items-center justify-center gap-3">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setScheduleMode(false);
                setScheduleError(null);
              }}
              className="px-3 py-1.5 rounded-full text-xs border-2 transition-all"
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
              className="px-3 py-1.5 rounded-full text-xs border-2 transition-all"
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
              onChange={(e) => {
                setScheduledAt(e.target.value);
                setScheduleError(null);
              }}
              className="text-xs bg-transparent border border-border/60 rounded px-2 py-1.5"
            />
          )}
          {(scheduleError || (scheduleMode && !scheduleError) || done || Object.keys(publishErrors).length > 0) && (
            <div className="text-center max-w-md">
              {scheduleError && (
                <p className="text-xs text-red-400 font-medium">{scheduleError}</p>
              )}
              {scheduleMode && !scheduleError && (
                <p className="text-[10px] text-muted-foreground/70 font-mono">
                  FB/IG ≥10 min · TikTok ≥15 min · YT any future time
                </p>
              )}
              {Object.entries(publishErrors).map(([k, msg]) => (
                <p key={k} className="text-[10px] text-red-400 font-mono truncate" title={msg}>
                  {k}: {msg}
                </p>
              ))}
              {done && Object.keys(publishErrors).length === 0 && (
                <p className="text-xs text-emerald-400 font-medium">
                  Done. Check each platform for live posts.
                </p>
              )}
            </div>
          )}
          <Button onClick={publish} disabled={!canPublish} size="lg" className="gap-2">
            {isPublishing ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Publishing…
              </>
            ) : scheduleMode ? (
              `Schedule on ${selected.size} platform${selected.size !== 1 ? "s" : ""}`
            ) : (
              `Post to ${selected.size} platform${selected.size !== 1 ? "s" : ""}`
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
