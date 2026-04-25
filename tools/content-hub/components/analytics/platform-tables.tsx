"use client";

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

export interface YtStat {
  video_id: string;
  title: string;
  url: string;
  published_at: string;
  views: number;
  likes: number;
  comments: number;
  fetched_at: string;
}

export type YtSortKey = "published_at" | "views" | "likes" | "comments";

export interface FbPost {
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

export type FbSortKey = "created_time" | "reactions" | "comments_count" | "shares_count" | "reach";

export interface IgPost {
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

export type IgSortKey = "timestamp" | "like_count" | "comments_count" | "saved" | "reach";

export interface TtStat {
  video_id: string;
  title: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
  published_at: string | null;
  updated_at: string;
}

// ─── YouTube ────────────────────────────────────────────────────────────────

export function YouTubeChart({ stats }: { stats: YtStat[] }) {
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

export function YouTubeTable({ stats, sortKey, sortDir, onSort, onSelect, selectedId }: {
  stats: YtStat[];
  sortKey: YtSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: YtSortKey) => void;
  onSelect?: (v: YtStat) => void;
  selectedId?: string | null;
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
            <tr
              key={v.video_id}
              className={`border-b border-border/40 hover:bg-muted/10 transition-colors ${selectedId === v.video_id ? "bg-[color:var(--brand)]/10" : ""} ${onSelect ? "cursor-pointer" : ""}`}
              onClick={onSelect ? () => onSelect(v) : undefined}
            >
              <td className="px-4 py-2 max-w-xs truncate">
                <a
                  href={v.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                  style={{ color: "var(--brand)" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {v.title}
                </a>
              </td>
              <td className="px-4 py-2 text-right text-xs text-muted-foreground">{v.published_at.slice(0, 10)}</td>
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

// ─── Facebook ────────────────────────────────────────────────────────────────

export function FacebookChart({ posts }: { posts: FbPost[] }) {
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

export function FacebookTable({ posts, sortKey, sortDir, onSort, onSelect, selectedId }: {
  posts: FbPost[];
  sortKey: FbSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: FbSortKey) => void;
  onSelect?: (p: FbPost) => void;
  selectedId?: string | null;
}) {
  const sorted = [...posts].sort((a, b) => {
    const av = a[sortKey] ?? 0, bv = b[sortKey] ?? 0;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  if (sorted.length === 0)
    return <p className="text-sm text-muted-foreground">No Facebook data. Hit "Refresh" to pull.</p>;

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
            <tr
              key={p.post_id}
              className={`border-b border-border/40 hover:bg-muted/10 transition-colors ${selectedId === p.post_id ? "bg-[color:var(--brand)]/10" : ""} ${onSelect ? "cursor-pointer" : ""}`}
              onClick={onSelect ? () => onSelect(p) : undefined}
            >
              <td className="px-4 py-2 max-w-xs">
                <div className="flex flex-col gap-0.5">
                  {p.permalink_url ? (
                    <a href={p.permalink_url} target="_blank" rel="noreferrer" className="hover:underline truncate block" style={{ color: "var(--brand)" }}
                      onClick={(e) => e.stopPropagation()}>
                      {(p.message ?? "(no caption)").slice(0, 60)}
                    </a>
                  ) : (
                    <span className="truncate text-muted-foreground">{(p.message ?? "(no caption)").slice(0, 60)}</span>
                  )}
                </div>
              </td>
              <td className="px-4 py-2 text-right text-xs text-muted-foreground">{p.created_time.slice(0, 10)}</td>
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

// ─── Instagram ───────────────────────────────────────────────────────────────

export function InstagramChart({ posts }: { posts: IgPost[] }) {
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

export function InstagramTable({ posts, sortKey, sortDir, onSort, onSelect, selectedId }: {
  posts: IgPost[];
  sortKey: IgSortKey;
  sortDir: "asc" | "desc";
  onSort: (key: IgSortKey) => void;
  onSelect?: (p: IgPost) => void;
  selectedId?: string | null;
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
            <tr
              key={p.post_id}
              className={`border-b border-border/40 hover:bg-muted/10 transition-colors ${selectedId === p.post_id ? "bg-[color:var(--brand)]/10" : ""} ${onSelect ? "cursor-pointer" : ""}`}
              onClick={onSelect ? () => onSelect(p) : undefined}
            >
              <td className="px-4 py-2 max-w-xs">
                <div className="flex flex-col gap-0.5">
                  {p.permalink ? (
                    <a href={p.permalink} target="_blank" rel="noreferrer" className="hover:underline truncate block" style={{ color: "var(--brand)" }}
                      onClick={(e) => e.stopPropagation()}>
                      {(p.caption ?? "(no caption)").slice(0, 60)}
                    </a>
                  ) : (
                    <span className="truncate text-muted-foreground">{(p.caption ?? "(no caption)").slice(0, 60)}</span>
                  )}
                  {p.media_type && <span className="text-xs text-muted-foreground">{p.media_type}</span>}
                </div>
              </td>
              <td className="px-4 py-2 text-right text-xs text-muted-foreground">{p.timestamp.slice(0, 10)}</td>
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

// ─── TikTok ──────────────────────────────────────────────────────────────────

export function TikTokTable({ stats, onSelect, selectedId }: {
  stats: TtStat[];
  onSelect?: (v: TtStat) => void;
  selectedId?: string | null;
}) {
  if (stats.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No TikTok data. Hit "Refresh from TikTok" to pull (requires TikTok OAuth).
      </p>
    );
  }
  const sorted = [...stats].sort(
    (a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""),
  );
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/20">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Title</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Published</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Views</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Likes</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Comments</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Shares</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((v) => (
            <tr
              key={v.video_id}
              className={`border-b border-border/40 hover:bg-muted/10 transition-colors ${selectedId === v.video_id ? "bg-[color:var(--brand)]/10" : ""} ${onSelect ? "cursor-pointer" : ""}`}
              onClick={onSelect ? () => onSelect(v) : undefined}
            >
              <td className="px-4 py-2 max-w-xs truncate">{v.title ?? v.video_id}</td>
              <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                {v.published_at ? new Date(v.published_at).toLocaleDateString() : "—"}
              </td>
              <td className="px-4 py-2 text-right font-mono">{v.view_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{v.like_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{v.comment_count.toLocaleString()}</td>
              <td className="px-4 py-2 text-right font-mono">{v.share_count.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
