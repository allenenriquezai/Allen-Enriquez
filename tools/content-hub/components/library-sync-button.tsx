"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";

export function LibrarySyncButton() {
  const [syncing, setSyncing] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);

  async function run() {
    setSyncing(true);
    setMsg(null);
    try {
      const res = await fetch("/api/library/sync", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "sync failed");
      setMsg(`+${data.inserted} new, ${data.skipped} existing, ${data.scanned} scanned`);
      setTimeout(() => window.location.reload(), 1200);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "sync failed");
      setSyncing(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {msg && <span className="text-xs text-muted-foreground">{msg}</span>}
      <button
        type="button"
        onClick={run}
        disabled={syncing}
        className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-60"
      >
        <RefreshCw className={`size-4 ${syncing ? "animate-spin" : ""}`} />
        {syncing ? "Syncing…" : "Sync from R2"}
      </button>
    </div>
  );
}
