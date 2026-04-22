"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MetricsTable, type MetricRow } from "@/components/metrics-table";
import { MetricsChart } from "@/components/metrics-chart";

const PLATFORMS = [
  { value: "all", label: "All" },
  { value: "facebook", label: "FB" },
  { value: "instagram", label: "IG" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
  { value: "x", label: "X" },
];

interface PostOption {
  id: number;
  platform: string;
  asset_title: string | null;
  asset_type: string | null;
}

export default function AnalyticsPage() {
  const [platform, setPlatform] = useState("all");
  const [rows, setRows] = useState<MetricRow[]>([]);
  const [posts, setPosts] = useState<PostOption[]>([]);

  const load = useCallback(async () => {
    const url =
      platform === "all"
        ? "/api/metrics"
        : `/api/metrics?platform=${encodeURIComponent(platform)}`;
    const res = await fetch(url, { cache: "no-store" });
    const json = await res.json();
    setRows(json.metrics ?? []);
  }, [platform]);

  const loadPosts = useCallback(async () => {
    const res = await fetch("/api/posts", { cache: "no-store" });
    const json = await res.json();
    setPosts(json.posts ?? []);
  }, []);

  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const kpis = useMemo(() => {
    const totalViews = rows.reduce((a, r) => a + (r.views ?? 0), 0);
    const totalEng = rows.reduce(
      (a, r) => a + (r.likes ?? 0) + (r.comments ?? 0) + (r.shares ?? 0) + (r.saves ?? 0),
      0,
    );
    const follows = rows.reduce((a, r) => a + (r.follows_gained ?? 0), 0);
    const ctr = totalViews > 0 ? (totalEng / totalViews) * 100 : 0;
    return { totalViews, totalEng, follows, ctr };
  }, [rows]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manual entry only. Auto-pull coming in Phase 2.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={platform}
            onValueChange={(v) => setPlatform(v ?? "all")}
          >
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PLATFORMS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <AddMetricsDialog posts={posts} onSaved={load} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Views" value={kpis.totalViews.toLocaleString()} />
        <KpiCard
          label="Total Engagement"
          value={kpis.totalEng.toLocaleString()}
        />
        <KpiCard
          label="Avg CTR proxy"
          value={`${kpis.ctr.toFixed(2)}%`}
        />
        <KpiCard
          label="Follows Gained"
          value={kpis.follows.toLocaleString()}
        />
      </div>

      <MetricsChart rows={rows} />
      <MetricsTable rows={rows} />
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-mono font-semibold">{value}</div>
      </CardContent>
    </Card>
  );
}

function AddMetricsDialog({
  posts,
  onSaved,
}: {
  posts: PostOption[];
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [postId, setPostId] = useState<string>("");
  const [form, setForm] = useState({
    views: 0,
    likes: 0,
    comments: 0,
    shares: 0,
    saves: 0,
    follows_gained: 0,
    recorded_at: new Date().toISOString().slice(0, 10),
  });

  const save = async () => {
    if (!postId) return;
    await fetch("/api/metrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: Number(postId), ...form }),
    });
    setOpen(false);
    setPostId("");
    onSaved();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>Add metrics</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add metrics</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Post</label>
            {posts.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No posts yet. Create an asset + post first (Library tab).
              </p>
            ) : (
              <select
                value={postId}
                onChange={(e) => setPostId(e.target.value)}
                className="h-8 rounded-lg bg-transparent border border-input px-2 text-sm"
              >
                <option value="">Select a post…</option>
                {posts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {(p.asset_title ?? `#${p.id}`) + " — " + p.platform}
                  </option>
                ))}
              </select>
            )}
          </div>
          <FormRow label="Views">
            <Input
              type="number"
              value={form.views}
              onChange={(e) =>
                setForm({ ...form, views: Number(e.target.value) })
              }
            />
          </FormRow>
          <div className="grid grid-cols-2 gap-2">
            <FormRow label="Likes">
              <Input
                type="number"
                value={form.likes}
                onChange={(e) =>
                  setForm({ ...form, likes: Number(e.target.value) })
                }
              />
            </FormRow>
            <FormRow label="Comments">
              <Input
                type="number"
                value={form.comments}
                onChange={(e) =>
                  setForm({ ...form, comments: Number(e.target.value) })
                }
              />
            </FormRow>
            <FormRow label="Shares">
              <Input
                type="number"
                value={form.shares}
                onChange={(e) =>
                  setForm({ ...form, shares: Number(e.target.value) })
                }
              />
            </FormRow>
            <FormRow label="Saves">
              <Input
                type="number"
                value={form.saves}
                onChange={(e) =>
                  setForm({ ...form, saves: Number(e.target.value) })
                }
              />
            </FormRow>
          </div>
          <FormRow label="Follows gained">
            <Input
              type="number"
              value={form.follows_gained}
              onChange={(e) =>
                setForm({ ...form, follows_gained: Number(e.target.value) })
              }
            />
          </FormRow>
          <FormRow label="Recorded at">
            <Input
              type="date"
              value={form.recorded_at}
              onChange={(e) =>
                setForm({ ...form, recorded_at: e.target.value })
              }
            />
          </FormRow>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={!postId}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FormRow({
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
