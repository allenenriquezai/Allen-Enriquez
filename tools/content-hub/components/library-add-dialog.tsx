"use client";

import * as React from "react";
import { Upload, X, Loader2 } from "lucide-react";

type AssetType = "reel" | "youtube" | "carousel";

const ACCEPT = "video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/gif";

type Idea = {
  id: number;
  title: string;
};

export function LibraryAddDialog({ onDone }: { onDone: () => void }) {
  const [file, setFile] = React.useState<File | null>(null);
  const [title, setTitle] = React.useState("");
  const [assetType, setAssetType] = React.useState<AssetType>("reel");
  const [ideaId, setIdeaId] = React.useState<number | null>(null);
  const [ideas, setIdeas] = React.useState<Idea[]>([]);
  const [status, setStatus] = React.useState<"idle" | "uploading" | "saving" | "done" | "error">("idle");
  const [progress, setProgress] = React.useState(0);
  const [error, setError] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Fetch ideas on mount
  React.useEffect(() => {
    const fetchIdeas = async () => {
      try {
        const res = await fetch("/api/ideas");
        if (res.ok) {
          const data = await res.json();
          if (data.ideas && Array.isArray(data.ideas)) {
            setIdeas(data.ideas);
          }
        }
      } catch (e) {
        // Gracefully degrade — log and skip
        console.warn("Failed to fetch ideas:", e instanceof Error ? e.message : "Unknown error");
      }
    };
    fetchIdeas();
  }, []);

  const inferType = (f: File): AssetType => {
    if (f.type.startsWith("image/")) return "carousel";
    return "reel";
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setAssetType(inferType(f));
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
  };

  const upload = async () => {
    if (!file) return;
    setError("");
    setStatus("uploading");
    setProgress(0);

    try {
      // 1. Get presigned URL
      const presignRes = await fetch("/api/upload/presigned", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, contentType: file.type }),
      });
      if (!presignRes.ok) throw new Error("Failed to get upload URL");
      const { uploadUrl, publicUrl } = await presignRes.json();

      // 2. PUT directly to R2 with XHR for progress
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", uploadUrl);
        xhr.setRequestHeader("Content-Type", file.type);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload failed: ${xhr.status}`)));
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.send(file);
      });

      setProgress(100);
      setStatus("saving");

      // 3. Create asset record
      const saveRes = await fetch("/api/library", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: file.name, type: assetType, title: title || null, url: publicUrl, idea_id: ideaId }),
      });
      if (!saveRes.ok) throw new Error("Failed to save asset");

      setStatus("done");
      setTimeout(onDone, 800);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        <button
          type="button"
          onClick={onDone}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" />
        </button>

        <h2 className="text-lg font-semibold mb-4">Add to Library</h2>

        {/* File picker */}
        <div
          onClick={() => inputRef.current?.click()}
          className="mb-4 flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/20 p-8 cursor-pointer hover:border-[var(--brand)] transition-colors"
        >
          <Upload className="size-8 text-muted-foreground" />
          {file ? (
            <span className="text-sm font-mono truncate max-w-[280px]">{file.name}</span>
          ) : (
            <span className="text-sm text-muted-foreground">Click to select video or image</span>
          )}
          <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={onFileChange} />
        </div>

        {/* Title */}
        <label className="block mb-3">
          <span className="text-xs font-mono uppercase text-muted-foreground">Title</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled"
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
          />
        </label>

        {/* Link to Idea */}
        {ideas.length > 0 && (
          <label className="block mb-3">
            <span className="text-xs font-mono uppercase text-muted-foreground">Link to Idea</span>
            <select
              value={ideaId ?? ""}
              onChange={(e) => setIdeaId(e.target.value ? parseInt(e.target.value, 10) : null)}
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
            >
              <option value="">— None —</option>
              {ideas.map((idea) => (
                <option key={idea.id} value={idea.id}>
                  {idea.title}
                </option>
              ))}
            </select>
          </label>
        )}

        {/* Type */}
        <label className="block mb-5">
          <span className="text-xs font-mono uppercase text-muted-foreground">Type</span>
          <select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value as AssetType)}
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--brand)]"
          >
            <option value="reel">Reel (short-form)</option>
            <option value="youtube">YouTube</option>
            <option value="carousel">Carousel</option>
          </select>
        </label>

        {/* Progress */}
        {(status === "uploading" || status === "saving") && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs font-mono text-muted-foreground mb-1">
              <span>{status === "saving" ? "Saving…" : `Uploading… ${progress}%`}</span>
              <Loader2 className="size-3 animate-spin" />
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${progress}%`, background: "var(--brand)" }}
              />
            </div>
          </div>
        )}

        {status === "done" && (
          <p className="mb-4 text-sm text-emerald-400 font-mono">Uploaded!</p>
        )}

        {error && (
          <p className="mb-4 text-sm text-red-400 font-mono">{error}</p>
        )}

        <button
          type="button"
          onClick={upload}
          disabled={!file || status === "uploading" || status === "saving" || status === "done"}
          className="w-full rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-40"
          style={{ background: "var(--brand)", color: "#000" }}
        >
          Upload
        </button>
      </div>
    </div>
  );
}
