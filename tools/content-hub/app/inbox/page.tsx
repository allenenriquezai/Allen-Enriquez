"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { InboxColumn, type InboxMessage } from "@/components/inbox-column";
import { RefreshCw } from "lucide-react";

type SyncState = "idle" | "syncing" | "done";

const SYNC_BUTTONS: { label: string; endpoint: string; disabled?: boolean; tooltip?: string }[] = [
  { label: "FB Comments", endpoint: "/api/facebook/comments?limit=50" },
  { label: "FB DMs", endpoint: "/api/facebook/conversations" },
  { label: "IG Comments", endpoint: "/api/instagram/comments?media_id=recent&limit=25" },
  { label: "IG DMs", endpoint: "/api/instagram/conversations" },
  { label: "YT Comments", endpoint: "/api/youtube/comments?limit=50" },
  { label: "TikTok", endpoint: "", disabled: true, tooltip: "Pending TikTok credentials" },
];

function SyncButton({ label, endpoint, disabled, tooltip, onDone }: {
  label: string;
  endpoint: string;
  disabled?: boolean;
  tooltip?: string;
  onDone: () => void;
}) {
  const [state, setState] = useState<SyncState>("idle");
  const [newCount, setNewCount] = useState<number | null>(null);

  const handleSync = async () => {
    if (disabled || !endpoint) return;
    setState("syncing");
    try {
      const res = await fetch(endpoint, { cache: "no-store" });
      const json = res.ok ? await res.json() : {};
      setNewCount(json.inserted ?? json.new ?? null);
      setState("done");
      onDone();
      setTimeout(() => { setState("idle"); setNewCount(null); }, 3000);
    } catch {
      setState("idle");
    }
  };

  return (
    <Button
      size="sm"
      variant="outline"
      disabled={disabled || state === "syncing"}
      title={tooltip}
      className="h-7 px-2.5 text-xs gap-1.5"
      style={state === "done" ? { color: "#22c55e", borderColor: "rgba(34,197,94,0.4)" } : disabled ? { opacity: 0.45 } : {}}
      onClick={handleSync}
    >
      <RefreshCw className={`h-3 w-3 ${state === "syncing" ? "animate-spin" : ""}`} />
      {state === "done"
        ? newCount !== null ? `${newCount} new` : "Done"
        : state === "syncing"
        ? "Syncing…"
        : label}
    </Button>
  );
}

const PLATFORMS = [
  { value: "all", label: "All" },
  { value: "facebook", label: "FB" },
  { value: "instagram", label: "IG" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
  { value: "x", label: "X" },
];

const THREAD_TYPES = ["comment", "dm", "mention"] as const;

export default function InboxPage() {
  const [platform, setPlatform] = useState("all");
  const [messages, setMessages] = useState<InboxMessage[]>([]);

  const load = useCallback(async () => {
    const url =
      platform === "all"
        ? "/api/inbox"
        : `/api/inbox?platform=${encodeURIComponent(platform)}`;
    const res = await fetch(url, { cache: "no-store" });
    const json = await res.json();
    setMessages(json.messages ?? []);
  }, [platform]);

  useEffect(() => {
    load();
  }, [load]);

  const { comments, dms, mentions } = useMemo(() => {
    const comments = messages.filter((m) => m.thread_type === "comment");
    const dms = messages.filter((m) => m.thread_type === "dm");
    const mentions = messages.filter((m) => m.thread_type === "mention");
    return { comments, dms, mentions };
  }, [messages]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Inbox</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Comments, DMs, and mentions across platforms.
          </p>
        </div>
        <AddMessageDialog onSaved={load} />
      </div>

      <div className="flex flex-wrap gap-1.5 items-center">
        <span className="text-xs text-muted-foreground mr-1">Sync:</span>
        {SYNC_BUTTONS.map((btn) => (
          <SyncButton
            key={btn.label}
            label={btn.label}
            endpoint={btn.endpoint}
            disabled={btn.disabled}
            tooltip={btn.tooltip}
            onDone={load}
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {PLATFORMS.map((p) => (
          <Button
            key={p.value}
            size="sm"
            variant={platform === p.value ? "default" : "outline"}
            onClick={() => setPlatform(p.value)}
          >
            {p.label}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <InboxColumn title="Comments" messages={comments} onRefresh={load} />
        <InboxColumn title="DMs" messages={dms} onRefresh={load} />
        <InboxColumn title="Mentions" messages={mentions} onRefresh={load} />
      </div>
    </div>
  );
}

function AddMessageDialog({ onSaved }: { onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    platform: "instagram",
    thread_type: "comment",
    author: "",
    thread_text: "",
    received_at: new Date().toISOString().slice(0, 16),
  });

  const save = async () => {
    if (!form.thread_text.trim()) return;
    await fetch("/api/inbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setOpen(false);
    setForm({ ...form, author: "", thread_text: "" });
    onSaved();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>Add message</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add message</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Platform">
              <select
                value={form.platform}
                onChange={(e) =>
                  setForm({ ...form, platform: e.target.value })
                }
                className="h-8 rounded-lg bg-transparent border border-input px-2 text-sm"
              >
                {PLATFORMS.filter((p) => p.value !== "all").map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Type">
              <select
                value={form.thread_type}
                onChange={(e) =>
                  setForm({ ...form, thread_type: e.target.value })
                }
                className="h-8 rounded-lg bg-transparent border border-input px-2 text-sm"
              >
                {THREAD_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Author">
            <Input
              value={form.author}
              onChange={(e) => setForm({ ...form, author: e.target.value })}
              placeholder="@handle"
            />
          </Field>
          <Field label="Message">
            <Textarea
              value={form.thread_text}
              onChange={(e) =>
                setForm({ ...form, thread_text: e.target.value })
              }
              className="min-h-24"
            />
          </Field>
          <Field label="Received at">
            <Input
              type="datetime-local"
              value={form.received_at}
              onChange={(e) =>
                setForm({ ...form, received_at: e.target.value })
              }
            />
          </Field>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={!form.thread_text.trim()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
