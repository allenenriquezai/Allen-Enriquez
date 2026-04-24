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
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
} from "recharts";

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

interface YtStat {
  video_id: string;
  title: string;
  url: string;
  published_at: string;
  views: number;
  likes: number;
  comments: number;
  fetched_at: string;
}

type YtSortKey = "published_at" | "views" | "likes" | "comments";

interface FbPost {
  post_id: string;
  message: string | null;
  created_time: string;
  permalink_url: string | null;
  impressions: number;
  reach: number;
  engaged_users: number;
  reactions: number;
  comments_count: number;
  shares_count: number;
}

type FbSortKey = "created_time" | "reactions" | "comments_count" | "shares_count" | "reach";

interface IgPost {
  post_id: string;
  caption: string | null;
  media_type: string | null;
  timestamp: string;
  permalink: string | null;
  like_count: number;
  comments_count: number;
  impressions: number;
  reach: number;
  saved: number;
}

type IgSortKey = "timestamp" | "like_count" | "comments_count" | "saved" | "reach";

export default function AnalyticsPage() {
  const [platform, setPlatform] = useState("all");
  const [rows, setRows] = useState<MetricRow[]>([]);
  const [posts, setPosts] = useState<PostOption[]>([]);
  const [ytStats, setYtStats] = useState<YtStat[]>([]);
  const [ytLoading, setYtLoading] = useState(false);
  const [ytSortKey, setYtSortKey] = useState<YtSortKey>("published_at");
  const [ytSortDir, setYtSortDir] = useState<"asc" | "desc">("desc");
  const [fbPosts, setFbPosts] = useState<FbPost[]>([]);
  const [fbLoading, setFbLoading] = useState(false);
  const [fbSortKey, setFbSortKey] = useState<FbSortKey>("created_time");
  const [fbSortDir, setFbSortDir] = useState<"asc" | "desc">("desc");
  const [igPosts, setIgPosts] = useState<IgPost[]>([]);
  const [igLoading, setIgLoading] = useState(false);
  const [igSortKey, setIgSortKey] = useState<IgSortKey>("timestamp");
  const [igSortDir, setIgSortDir] = useState<"asc" | "desc">("desc");

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

  const loadYouTube = useCallback(async (refresh = false) => {
    setYtLoading(true);
    try {
      const res = await fetch(`/api/analytics/youtube${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setYtStats(json.stats ?? []);
    } finally {
      setYtLoading(false);
    }
  }, []);

  const loadFacebook = useCallback(async (refresh = false) => {
    setFbLoading(true);
    try {
      const res = await fetch(`/api/analytics/facebook${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setFbPosts(json.posts ?? []);
    } finally {
      setFbLoading(false);
    }
  }, []);

  const loadInstagram = useCallback(async (refresh = false) => {
    setIgLoading(true);
    try {
      const res = await fetch(`/api/analytics/instagram${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setIgPosts(json.posts ?? []);
    } finally {
      setIgLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadPosts(); }, [loadPosts]);
  useEffect(() => { loadYouTube(); }, [loadYouTube]);
  useEffect(() => { loadFacebook(); }, [loadFacebook]);
  useEffect(() => { loadInstagram(); }, [loadInstagram]);

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
            Use the Refresh buttons below to pull latest data from each platform.
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

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">YouTube Videos</h2>
          <Button size="sm" variant="outline" disabled={ytLoading} onClick={() => loadYouTube(true)}>
            {ytLoading ? "Refreshing…" : "Refresh from YouTube"}
          </Button>
        </div>
        <YouTubeChart stats={ytStats} />
        <div className="mt-4">
          <YouTubeTable
            stats={ytStats}
            sortKey={ytSortKey}
            sortDir={ytSortDir}
            onSort={(key) => {
              if (key === ytSortKey) setYtSortDir(d => d === "asc" ? "desc" : "asc");
              else { setYtSortKey(key); setYtSortDir("desc"); }
            }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Facebook Page</h2>
            <Button size="sm" variant="outline" disabled={fbLoading} onClick={() => loadFacebook(true)}>
              {fbLoading ? "Refreshing…" : "Refresh"}
            </Button>
          </div>
          <FacebookChart posts={fbPosts} />
          <div className="mt-4">
            <FacebookTable
              posts={fbPosts}
              sortKey={fbSortKey}
              sortDir={fbSortDir}
              onSort={(key) => {
                if (key === fbSortKey) setFbSortDir(d => d === "asc" ? "desc" : "asc");
                else { setFbSortKey(key); setFbSortDir("desc"); }
              }}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Instagram</h2>
            <Button size="sm" variant="outline" disabled={igLoading} onClick={() => loadInstagram(true)}>
              {igLoading ? "Refreshing…" : "Refresh"}
            </Button>
          </div>
          <InstagramChart posts={igPosts} />
          <div className="mt-4">
            <InstagramTable
              posts={igPosts}
              sortKey={igSortKey}
              sortDir={igSortDir}
              onSort={(key) => {
                if (key === igSortKey) setIgSortDir(d => d === "asc" ? "desc" : "asc");
                else { setIgSortKey(key); setIgSortDir("desc"); }
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function YouTubeChart({ stats }: { stats: YtStat[] }) {
  if (stats.length === 0) return null;

  const data = [...stats]
    .sort((a, b) => a.published_at.localeCompare(b.published_at))
    .map((v) => ({
      label: v.published_at.slice(5, 10),
      title: v.title.length > 40 ? v.title.slice(0, 38) + "…" : v.title,
      views: v.views,
      likes: v.likes,
      comments: v.comments,
      engRate: v.views > 0 ? +((v.likes + v.comments) / v.views * 100).toFixed(1) : 0,
    }));

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: typeof data[0] }[] }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="rounded-lg border border-border bg-[#1b1b1b] p-3 text-xs space-y-1 max-w-[220px]">
        <p className="font-medium text-foreground leading-snug">{d.title}</p>
        <p className="text-muted-foreground">{d.label}</p>
        <div className="flex gap-3 pt-1">
          <span style={{ color: "#02B3E9" }}>{d.views.toLocaleString()} views</span>
          <span style={{ color: "#f59e0b" }}>{d.likes} likes</span>
          <span style={{ color: "#a855f7" }}>{d.comments} comments</span>
        </div>
        <p className="text-muted-foreground">Eng rate: {d.engRate}%</p>
      </div>
    );
  };

  return (
    <div className="h-64 rounded-xl ring-1 ring-foreground/10 p-3 mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="label" stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <YAxis yAxisId="left" stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <YAxis yAxisId="right" orientation="right" stroke="rgba(255,255,255,0.3)" fontSize={10}
            tickFormatter={(v) => `${v}%`} domain={[0, "auto"]} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar yAxisId="left" dataKey="views" fill="#02B3E9" opacity={0.85} radius={[3, 3, 0, 0]} name="Views" />
          <Line yAxisId="right" type="monotone" dataKey="engRate" stroke="#f59e0b"
            strokeWidth={2} dot={{ r: 3 }} name="Eng %" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function YouTubeTable({ stats, sortKey, sortDir, onSort }: {
  stats: YtStat[];
  sortKey: YtSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: YtSortKey) => void;
}) {
  const sorted = [...stats].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  if (sorted.length === 0)
    return <p className="text-sm text-muted-foreground">No YouTube data. Hit "Refresh from YouTube" to pull.</p>;

  const cols: { key: YtSortKey; label: string }[] = [
    { key: "published_at", label: "Published" },
    { key: "views", label: "Views" },
    { key: "likes", label: "Likes" },
    { key: "comments", label: "Comments" },
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/20">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Title</th>
            {cols.map(c => (
              <th
                key={c.key}
                className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer select-none hover:text-foreground transition-colors"
                onClick={() => onSort(c.key)}
              >
                {c.label}{sortKey === c.key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(v => (
            <tr key={v.video_id} className="border-b border-border/40 hover:bg-muted/10 transition-colors">
              <td className="px-4 py-2 max-w-xs truncate">
                <a href={v.url} target="_blank" rel="noreferrer" className="hover:underline" style={{ color: "var(--brand)" }}>
                  {v.title}
                </a>
              </td>
              <td className="px-4 py-2 text-right font-mono">{v.views.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{v.likes.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{v.comments.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FacebookChart({ posts }: { posts: FbPost[] }) {
  if (posts.length === 0) return null;

  const data = [...posts]
    .sort((a, b) => a.created_time.localeCompare(b.created_time))
    .map((p) => ({
      label: p.created_time.slice(5, 10),
      msg: (p.message ?? "").slice(0, 40) + ((p.message ?? "").length > 40 ? "…" : ""),
      reactions: p.reactions,
      comments: p.comments_count,
      shares: p.shares_count,
      reach: p.reach,
    }));

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: typeof data[0] }[] }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="rounded-lg border border-border bg-[#1b1b1b] p-3 text-xs space-y-1 max-w-[220px]">
        <p className="font-medium text-foreground leading-snug">{d.msg || "(no caption)"}</p>
        <p className="text-muted-foreground">{d.label}</p>
        <div className="flex gap-3 pt-1">
          <span style={{ color: "#02B3E9" }}>{d.reactions} reactions</span>
          <span style={{ color: "#f59e0b" }}>{d.comments} comments</span>
          <span style={{ color: "#a855f7" }}>{d.shares} shares</span>
        </div>
        {d.reach > 0 && <p className="text-muted-foreground">Reach: {d.reach.toLocaleString()}</p>}
      </div>
    );
  };

  return (
    <div className="h-64 rounded-xl ring-1 ring-foreground/10 p-3 mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="label" stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <YAxis stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="reactions" fill="#02B3E9" opacity={0.85} radius={[3, 3, 0, 0]} name="Reactions" />
          <Bar dataKey="comments" fill="#f59e0b" opacity={0.85} radius={[3, 3, 0, 0]} name="Comments" />
          <Bar dataKey="shares" fill="#a855f7" opacity={0.85} radius={[3, 3, 0, 0]} name="Shares" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FacebookTable({ posts, sortKey, sortDir, onSort }: {
  posts: FbPost[];
  sortKey: FbSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: FbSortKey) => void;
}) {
  const sorted = [...posts].sort((a, b) => {
    const av = a[sortKey] ?? 0, bv = b[sortKey] ?? 0;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  if (sorted.length === 0)
    return <p className="text-sm text-muted-foreground">No Facebook data. Hit "Refresh from Facebook" to pull.</p>;

  const hasReach = sorted.some(p => p.reach > 0);

  const cols: { key: FbSortKey; label: string }[] = [
    { key: "created_time", label: "Date" },
    { key: "reactions", label: "Reactions" },
    { key: "comments_count", label: "Comments" },
    { key: "shares_count", label: "Shares" },
    ...(hasReach ? [{ key: "reach" as FbSortKey, label: "Reach" }] : []),
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/20">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Post</th>
            {cols.map(c => (
              <th
                key={c.key}
                className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer select-none hover:text-foreground transition-colors"
                onClick={() => onSort(c.key)}
              >
                {c.label}{sortKey === c.key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(p => (
            <tr key={p.post_id} className="border-b border-border/40 hover:bg-muted/10 transition-colors">
              <td className="px-4 py-2 max-w-xs">
                <div className="flex flex-col gap-0.5">
                  {p.permalink_url ? (
                    <a href={p.permalink_url} target="_blank" rel="noreferrer" className="hover:underline truncate block" style={{ color: "var(--brand)" }}>
                      {(p.message ?? "(no caption)").slice(0, 60)}
                    </a>
                  ) : (
                    <span className="truncate text-muted-foreground">{(p.message ?? "(no caption)").slice(0, 60)}</span>
                  )}
                  <span className="text-xs text-muted-foreground">{p.created_time.slice(0, 10)}</span>
                </div>
              </td>
              <td className="px-4 py-2 text-right font-mono">{p.reactions.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{p.comments_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{p.shares_count.toLocaleString()}</td>
              {hasReach && <td className="px-4 py-2 text-right font-mono">{p.reach.toLocaleString()}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InstagramChart({ posts }: { posts: IgPost[] }) {
  if (posts.length === 0) return null;

  const data = [...posts]
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    .map((p) => ({
      label: p.timestamp.slice(5, 10),
      caption: (p.caption ?? "").slice(0, 40) + ((p.caption ?? "").length > 40 ? "…" : ""),
      likes: p.like_count,
      comments: p.comments_count,
      saved: p.saved,
      reach: p.reach,
    }));

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: typeof data[0] }[] }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="rounded-lg border border-border bg-[#1b1b1b] p-3 text-xs space-y-1 max-w-[220px]">
        <p className="font-medium text-foreground leading-snug">{d.caption || "(no caption)"}</p>
        <p className="text-muted-foreground">{d.label}</p>
        <div className="flex gap-3 pt-1">
          <span style={{ color: "#e1306c" }}>{d.likes} likes</span>
          <span style={{ color: "#f59e0b" }}>{d.comments} comments</span>
          <span style={{ color: "#a855f7" }}>{d.saved} saved</span>
        </div>
        {d.reach > 0 && <p className="text-muted-foreground">Reach: {d.reach.toLocaleString()}</p>}
      </div>
    );
  };

  return (
    <div className="h-64 rounded-xl ring-1 ring-foreground/10 p-3 mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="label" stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <YAxis stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="likes" fill="#e1306c" opacity={0.85} radius={[3, 3, 0, 0]} name="Likes" />
          <Bar dataKey="comments" fill="#f59e0b" opacity={0.85} radius={[3, 3, 0, 0]} name="Comments" />
          <Bar dataKey="saved" fill="#a855f7" opacity={0.85} radius={[3, 3, 0, 0]} name="Saved" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function InstagramTable({ posts, sortKey, sortDir, onSort }: {
  posts: IgPost[];
  sortKey: IgSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: IgSortKey) => void;
}) {
  const sorted = [...posts].sort((a, b) => {
    const av = a[sortKey] ?? 0, bv = b[sortKey] ?? 0;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  if (sorted.length === 0)
    return <p className="text-sm text-muted-foreground">No Instagram data. Hit "Refresh" to pull.</p>;

  const hasReach = sorted.some(p => p.reach > 0);

  const cols: { key: IgSortKey; label: string }[] = [
    { key: "timestamp", label: "Date" },
    { key: "like_count", label: "Likes" },
    { key: "comments_count", label: "Comments" },
    { key: "saved", label: "Saved" },
    ...(hasReach ? [{ key: "reach" as IgSortKey, label: "Reach" }] : []),
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/20">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Post</th>
            {cols.map(c => (
              <th
                key={c.key}
                className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer select-none hover:text-foreground transition-colors"
                onClick={() => onSort(c.key)}
              >
                {c.label}{sortKey === c.key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(p => (
            <tr key={p.post_id} className="border-b border-border/40 hover:bg-muted/10 transition-colors">
              <td className="px-4 py-2 max-w-xs">
                <div className="flex flex-col gap-0.5">
                  {p.permalink ? (
                    <a href={p.permalink} target="_blank" rel="noreferrer" className="hover:underline truncate block" style={{ color: "var(--brand)" }}>
                      {(p.caption ?? "(no caption)").slice(0, 60)}
                    </a>
                  ) : (
                    <span className="truncate text-muted-foreground">{(p.caption ?? "(no caption)").slice(0, 60)}</span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {p.timestamp.slice(0, 10)}{p.media_type ? ` · ${p.media_type}` : ""}
                  </span>
                </div>
              </td>
              <td className="px-4 py-2 text-right font-mono">{p.like_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{p.comments_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{p.saved.toLocaleString()}</td>
              {hasReach && <td className="px-4 py-2 text-right font-mono">{p.reach.toLocaleString()}</td>}
            </tr>
          ))}
        </tbody>
      </table>
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
