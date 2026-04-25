"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Copy, Check, CheckCircle2, Send, Zap } from "lucide-react";

export type Caption = { variant: string; body: string };

export type QueueSlot = {
  schedule_id: number;
  slot_date: string;
  slot_type: string;
  status: string;
  notes: string | null;
  idea_id: number | null;
  title: string | null;
  pillar: string | null;
  captions: Caption[];
  reel_body: string | null;
  asset_id: number | null;
  asset_url: string | null;
  asset_title: string | null;
  asset_type: string | null;
};

const PLATFORM_TABS: { key: string; label: string }[] = [
  { key: "caption_ig", label: "IG / FB" },
  { key: "caption_tiktok", label: "TikTok" },
  { key: "caption_yt", label: "YT Shorts" },
  { key: "caption_x", label: "X" },
  { key: "caption_linkedin", label: "LinkedIn" },
];

const SLOT_LABELS: Record<string, string> = {
  reel_1: "Short-form · Slot 1",
  reel_2: "Short-form · Slot 2",
  carousel: "Carousel",
  youtube: "Long-form",
  fb_post: "FB Post",
};

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, React.CSSProperties> = {
    filmed: { color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.08)" },
    edited: { color: "var(--brand)", border: "1px solid rgba(2,179,233,0.3)", background: "rgba(2,179,233,0.08)" },
    planned: { color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.08)" },
    posted: { color: "var(--muted-foreground)", border: "1px solid rgba(128,128,128,0.2)", background: "rgba(128,128,128,0.06)" },
  };
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-[0.68rem] font-semibold uppercase tracking-wide"
      style={styles[status] ?? { border: "1px solid var(--border)" }}
    >
      {status}
    </span>
  );
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

export function QueueClient({ slots, ytConnected = false, tikConnected = false }: { slots: QueueSlot[]; ytConnected?: boolean; tikConnected?: boolean }) {
  const router = useRouter();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [postingId, setPostingId] = useState<number | null>(null);
  const [reschedulingId, setReschedulingId] = useState<number | null>(null);
  const [blotatoId, setBlotatoId] = useState<number | null>(null);
  const [blotatoFlash, setBlotatoFlash] = useState<Set<number>>(new Set());
  const [fbId, setFbId] = useState<number | null>(null);
  const [fbFlash, setFbFlash] = useState<Set<number>>(new Set());
  // IG publish state
  const [igUrlOpen, setIgUrlOpen] = useState<number | null>(null);
  const [igUrl, setIgUrl] = useState<Record<number, string>>({});
  const [igId, setIgId] = useState<number | null>(null);
  const [igFlash, setIgFlash] = useState<Set<number>>(new Set());
  // YT publish state
  const [ytUrlOpen, setYtUrlOpen] = useState<number | null>(null);
  const [ytUrl, setYtUrl] = useState<Record<number, string>>({});
  const [ytId, setYtId] = useState<number | null>(null);
  const [ytFlash, setYtFlash] = useState<Set<number>>(new Set());
  // TikTok publish state
  const [tikUrlOpen, setTikUrlOpen] = useState<number | null>(null);
  const [tikUrl, setTikUrl] = useState<Record<number, string>>({});
  const [tikId, setTikId] = useState<number | null>(null);
  const [tikFlash, setTikFlash] = useState<Set<number>>(new Set());

  const handleCopy = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  async function handleReschedule(scheduleId: number, newDate: string) {
    setReschedulingId(scheduleId);
    await fetch(`/api/schedule/${scheduleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slot_date: newDate }),
    });
    setReschedulingId(null);
    router.refresh();
  }

  const handleFbPost = async (scheduleId: number, message: string) => {
    setFbId(scheduleId);
    try {
      const res = await fetch("/api/facebook/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (res.ok) {
        setFbFlash((prev) => new Set(prev).add(scheduleId));
        setTimeout(() => setFbFlash((prev) => { const n = new Set(prev); n.delete(scheduleId); return n; }), 3000);
      }
    } finally {
      setFbId(null);
    }
  };

  const handleBlotato = async (scheduleId: number) => {
    setBlotatoId(scheduleId);
    try {
      const res = await fetch("/api/blotato/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schedule_id: scheduleId }),
      });
      if (res.ok) {
        setBlotatoFlash((prev) => new Set(prev).add(scheduleId));
        setTimeout(() => setBlotatoFlash((prev) => { const n = new Set(prev); n.delete(scheduleId); return n; }), 3000);
        router.refresh();
      }
    } finally {
      setBlotatoId(null);
    }
  };

  const handleIgPost = async (scheduleId: number, caption: string) => {
    const url = igUrl[scheduleId];
    if (!url) return;
    setIgId(scheduleId);
    try {
      const res = await fetch("/api/instagram/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caption, media_url: url, media_type: "REELS" }),
      });
      if (res.ok) {
        setIgFlash((prev) => new Set(prev).add(scheduleId));
        setTimeout(() => setIgFlash((prev) => { const n = new Set(prev); n.delete(scheduleId); return n; }), 3000);
        setIgUrlOpen(null);
      }
    } finally {
      setIgId(null);
    }
  };

  const handleYtPost = async (scheduleId: number, title: string, description: string) => {
    const url = ytUrl[scheduleId];
    if (!url) return;
    setYtId(scheduleId);
    try {
      const res = await fetch("/api/youtube/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, media_url: url }),
      });
      if (res.ok) {
        setYtFlash((prev) => new Set(prev).add(scheduleId));
        setTimeout(() => setYtFlash((prev) => { const n = new Set(prev); n.delete(scheduleId); return n; }), 3000);
        setYtUrlOpen(null);
      }
    } finally {
      setYtId(null);
    }
  };

  const handleTikPost = async (scheduleId: number, title: string, description: string) => {
    const url = tikUrl[scheduleId];
    if (!url) return;
    setTikId(scheduleId);
    try {
      const res = await fetch("/api/tiktok/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, video_url: url }),
      });
      if (res.ok) {
        setTikFlash((prev) => new Set(prev).add(scheduleId));
        setTimeout(() => setTikFlash((prev) => { const n = new Set(prev); n.delete(scheduleId); return n; }), 3000);
        setTikUrlOpen(null);
      }
    } finally {
      setTikId(null);
    }
  };

  const handleMarkPosted = async (scheduleId: number) => {
    setPostingId(scheduleId);
    try {
      await fetch(`/api/schedule/${scheduleId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "posted" }),
      });
      router.refresh();
    } finally {
      setPostingId(null);
    }
  };

  if (slots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No upcoming posts scheduled. Add slots in Calendar.
      </p>
    );
  }

  return (
    <>
    <div className="flex flex-col gap-4">
      {slots.map((slot) => {
        const captionMap: Record<string, string> = {};
        for (const c of slot.captions) captionMap[c.variant] = c.body;
        const hasCaptions = slot.captions.length > 0;
        const availableTabs = PLATFORM_TABS.filter(t => captionMap[t.key]);

        return (
          <Card key={slot.schedule_id} className="overflow-hidden">
            <CardHeader className="pb-3 border-b border-border space-y-0">
              {/* Row 1: status + date + slot type */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={slot.status} />
                  <span
                    className="text-sm font-medium"
                    style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.04em" }}
                  >
                    {formatDate(slot.slot_date)}
                  </span>
                  {slot.notes && (
                    <span
                      className="text-xs"
                      style={{ color: "var(--brand)", fontFamily: "var(--font-roboto-mono)" }}
                    >
                      · {slot.notes}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="ae-mono-label opacity-60">
                    {SLOT_LABELS[slot.slot_type] ?? slot.slot_type}
                  </span>
                  <input
                    type="date"
                    defaultValue={slot.slot_date}
                    className="text-xs bg-transparent border border-border/50 rounded px-1.5 py-0.5 text-muted-foreground hover:border-border transition-colors"
                    disabled={reschedulingId === slot.schedule_id}
                    onBlur={(e) => {
                      if (e.target.value && e.target.value !== slot.slot_date) {
                        handleReschedule(slot.schedule_id, e.target.value);
                      }
                    }}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 px-2.5 text-xs gap-1.5"
                    disabled={postingId === slot.schedule_id}
                    onClick={() => handleMarkPosted(slot.schedule_id)}
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    {postingId === slot.schedule_id ? "Saving…" : "Mark Posted"}
                  </Button>
                  {slot.asset_url ? (
                    <Button
                      size="sm"
                      className="h-7 px-2.5 text-xs gap-1.5"
                      style={{ background: "rgba(2,179,233,0.15)", color: "var(--brand)", border: "1px solid rgba(2,179,233,0.3)" }}
                      onClick={() => slot.asset_id && router.push(`/library/${slot.asset_id}`)}
                    >
                      <Zap className="h-3 w-3" />
                      Open Post
                    </Button>
                  ) : (
                    <span className="text-[10px] font-mono text-muted-foreground/40 px-1">No asset linked</span>
                  )}
                  {slot.reel_body && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 px-2.5 text-xs gap-1.5"
                      style={blotatoFlash.has(slot.schedule_id) ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : {}}
                      disabled={blotatoId === slot.schedule_id}
                      onClick={() => handleBlotato(slot.schedule_id)}
                    >
                      <Send className="h-3 w-3" />
                      {blotatoFlash.has(slot.schedule_id) ? "Posted to Blotato" : blotatoId === slot.schedule_id ? "Publishing…" : "Blotato"}
                    </Button>
                  )}
                  {captionMap["caption_ig"] && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 px-2.5 text-xs gap-1.5"
                      style={fbFlash.has(slot.schedule_id) ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : { color: "#1877F2", borderColor: "rgba(24,119,242,0.3)" }}
                      disabled={fbId === slot.schedule_id}
                      onClick={() => handleFbPost(slot.schedule_id, captionMap["caption_ig"])}
                    >
                      <Send className="h-3 w-3" />
                      {fbFlash.has(slot.schedule_id) ? "Posted to FB" : fbId === slot.schedule_id ? "Posting…" : "Post to FB"}
                    </Button>
                  )}
                  {captionMap["caption_ig"] && (
                    igUrlOpen === slot.schedule_id ? (
                      <span className="flex items-center gap-1">
                        <input
                          type="url"
                          placeholder="Media URL"
                          value={igUrl[slot.schedule_id] ?? ""}
                          onChange={(e) => setIgUrl((prev) => ({ ...prev, [slot.schedule_id]: e.target.value }))}
                          className="h-7 text-xs bg-transparent border border-border/60 rounded px-2 w-44"
                          autoFocus
                        />
                        <Button
                          size="sm"
                          className="h-7 px-2.5 text-xs gap-1.5"
                          disabled={igId === slot.schedule_id || !igUrl[slot.schedule_id]}
                          style={{ color: "#E1306C", background: "rgba(225,48,108,0.1)", border: "1px solid rgba(225,48,108,0.3)" }}
                          onClick={() => handleIgPost(slot.schedule_id, captionMap["caption_ig"])}
                        >
                          {igId === slot.schedule_id ? "Posting…" : "Confirm"}
                        </Button>
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setIgUrlOpen(null)}>✕</Button>
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2.5 text-xs gap-1.5"
                        style={igFlash.has(slot.schedule_id) ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : { color: "#E1306C", borderColor: "rgba(225,48,108,0.3)" }}
                        onClick={() => setIgUrlOpen(slot.schedule_id)}
                      >
                        <Send className="h-3 w-3" />
                        {igFlash.has(slot.schedule_id) ? "Posted to IG" : "Post to IG"}
                      </Button>
                    )
                  )}
                  {captionMap["caption_tiktok"] && (
                    tikConnected ? (
                      tikUrlOpen === slot.schedule_id ? (
                        <span className="flex items-center gap-1">
                          <input
                            type="url"
                            placeholder="Video URL"
                            value={tikUrl[slot.schedule_id] ?? ""}
                            onChange={(e) => setTikUrl((prev) => ({ ...prev, [slot.schedule_id]: e.target.value }))}
                            className="h-7 text-xs bg-transparent border border-border/60 rounded px-2 w-44"
                            autoFocus
                          />
                          <Button
                            size="sm"
                            className="h-7 px-2.5 text-xs gap-1.5"
                            disabled={tikId === slot.schedule_id || !tikUrl[slot.schedule_id]}
                            style={{ color: "#010101", background: "rgba(1,1,1,0.08)", border: "1px solid rgba(1,1,1,0.3)" }}
                            onClick={() => handleTikPost(slot.schedule_id, slot.title ?? "Untitled", captionMap["caption_tiktok"] ?? "")}
                          >
                            {tikId === slot.schedule_id ? "Uploading…" : "Confirm"}
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setTikUrlOpen(null)}>✕</Button>
                        </span>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2.5 text-xs gap-1.5"
                          style={tikFlash.has(slot.schedule_id) ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : { color: "#010101", borderColor: "rgba(1,1,1,0.3)" }}
                          onClick={() => setTikUrlOpen(slot.schedule_id)}
                        >
                          <Send className="h-3 w-3" />
                          {tikFlash.has(slot.schedule_id) ? "Posted to TikTok" : "Post to TikTok"}
                        </Button>
                      )
                    ) : (
                      <a
                        href="/api/tiktok/auth"
                        className="inline-flex items-center gap-1.5 h-7 px-2.5 text-xs rounded border"
                        style={{ color: "#010101", borderColor: "rgba(1,1,1,0.3)" }}
                      >
                        Connect TikTok →
                      </a>
                    )
                  )}
                  {slot.slot_type === "youtube" && (
                    ytConnected ? (
                      ytUrlOpen === slot.schedule_id ? (
                        <span className="flex items-center gap-1">
                          <input
                            type="url"
                            placeholder="Video URL"
                            value={ytUrl[slot.schedule_id] ?? ""}
                            onChange={(e) => setYtUrl((prev) => ({ ...prev, [slot.schedule_id]: e.target.value }))}
                            className="h-7 text-xs bg-transparent border border-border/60 rounded px-2 w-44"
                            autoFocus
                          />
                          <Button
                            size="sm"
                            className="h-7 px-2.5 text-xs gap-1.5"
                            disabled={ytId === slot.schedule_id || !ytUrl[slot.schedule_id]}
                            style={{ color: "#FF0000", background: "rgba(255,0,0,0.08)", border: "1px solid rgba(255,0,0,0.3)" }}
                            onClick={() => handleYtPost(slot.schedule_id, slot.title ?? "Untitled", captionMap["caption_yt"] ?? "")}
                          >
                            {ytId === slot.schedule_id ? "Uploading…" : "Confirm"}
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setYtUrlOpen(null)}>✕</Button>
                        </span>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2.5 text-xs gap-1.5"
                          style={ytFlash.has(slot.schedule_id) ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : { color: "#FF0000", borderColor: "rgba(255,0,0,0.3)" }}
                          onClick={() => setYtUrlOpen(slot.schedule_id)}
                        >
                          <Send className="h-3 w-3" />
                          {ytFlash.has(slot.schedule_id) ? "Uploaded to YT" : "Post to YT"}
                        </Button>
                      )
                    ) : (
                      <a
                        href="/api/youtube/auth"
                        className="inline-flex items-center gap-1.5 h-7 px-2.5 text-xs rounded border"
                        style={{ color: "#FF0000", borderColor: "rgba(255,0,0,0.3)" }}
                      >
                        Connect YouTube →
                      </a>
                    )
                  )}
                </div>
              </div>
              {/* Row 2: title + pillar */}
              {slot.title && (
                <div className="pt-2 flex items-center gap-2 flex-wrap">
                  <h2 className="text-base font-semibold leading-tight">{slot.title}</h2>
                  {slot.pillar && (
                    <Badge variant="outline" className="text-[0.68rem] px-1.5 py-0">
                      {slot.pillar.replace("_", " ")}
                    </Badge>
                  )}
                </div>
              )}
            </CardHeader>

            <CardContent className="pt-4 pb-5">
              {slot.reel_body && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">Script</p>
                  <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed p-4 rounded-lg bg-muted/10 border border-border/30 max-h-48 overflow-y-auto">
                    {slot.reel_body}
                  </pre>
                </div>
              )}
              {!hasCaptions ? (
                <p className="text-sm text-muted-foreground">No captions written yet.</p>
              ) : (
                <Tabs defaultValue={availableTabs[0]?.key ?? "caption_ig"}>
                  <TabsList className="mb-3 h-8">
                    {availableTabs.map(tab => (
                      <TabsTrigger key={tab.key} value={tab.key} className="text-xs px-3">
                        {tab.label}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {availableTabs.map(tab => {
                    const body = captionMap[tab.key];
                    const copyKey = `${slot.schedule_id}-${tab.key}`;
                    const copied = copiedKey === copyKey;
                    return (
                      <TabsContent key={tab.key} value={tab.key} className="mt-0">
                        <div className="relative group">
                          <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed p-4 pr-20 rounded-lg bg-muted/20 border border-border/40 min-h-[80px]">
                            {body}
                          </pre>
                          <Button
                            size="sm"
                            variant="outline"
                            className="absolute top-3 right-3 h-7 px-2.5 text-xs gap-1.5 opacity-70 hover:opacity-100 transition-opacity"
                            onClick={() => handleCopy(body, copyKey)}
                          >
                            {copied ? (
                              <>
                                <Check className="h-3 w-3" style={{ color: "#22c55e" }} />
                                <span style={{ color: "#22c55e" }}>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </Button>
                        </div>
                      </TabsContent>
                    );
                  })}
                </Tabs>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
    </>
  );
}
