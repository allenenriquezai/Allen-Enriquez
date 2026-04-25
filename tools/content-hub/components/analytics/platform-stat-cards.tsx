"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { YtStat, FbPost, IgPost, TtStat } from "@/components/analytics/platform-tables";
import type { MetricRow } from "@/components/metrics-table";

export function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-mono font-semibold">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
      </CardContent>
    </Card>
  );
}

type PlatformStatCardsProps =
  | { platform: "youtube"; stats: YtStat[]; subscriberCount: number | null }
  | { platform: "tiktok"; stats: TtStat[] }
  | { platform: "instagram"; stats: IgPost[] }
  | { platform: "facebook"; stats: FbPost[] }
  | { platform: "overview"; rows: MetricRow[] };

export function PlatformStatCards(props: PlatformStatCardsProps) {
  if (props.platform === "youtube") {
    const { stats, subscriberCount } = props;
    const totalViews = stats.reduce((a, v) => a + v.views, 0);
    const avgEng =
      stats.length > 0
        ? stats.reduce((a, v) => a + (v.views > 0 ? ((v.likes + v.comments) / v.views) * 100 : 0), 0) /
          stats.length
        : 0;
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          label="Subscribers"
          value={subscriberCount != null ? subscriberCount.toLocaleString() : "—"}
          sub={subscriberCount == null ? "refresh to load" : undefined}
        />
        <KpiCard label="Avg Watch Time" value="—" sub="click a video to see" />
        <KpiCard label="Avg Engagement" value={`${avgEng.toFixed(2)}%`} />
        <KpiCard label="Total Views" value={totalViews.toLocaleString()} />
      </div>
    );
  }

  if (props.platform === "tiktok") {
    const { stats } = props;
    const totalViews = stats.reduce((a, v) => a + v.view_count, 0);
    const totalLikes = stats.reduce((a, v) => a + v.like_count, 0);
    const totalShares = stats.reduce((a, v) => a + v.share_count, 0);
    const avgEng =
      stats.length > 0
        ? stats.reduce(
            (a, v) =>
              a +
              (v.view_count > 0
                ? ((v.like_count + v.comment_count + v.share_count) / v.view_count) * 100
                : 0),
            0,
          ) / stats.length
        : 0;
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Views" value={totalViews.toLocaleString()} />
        <KpiCard label="Total Shares" value={totalShares.toLocaleString()} />
        <KpiCard label="Avg Engagement" value={`${avgEng.toFixed(2)}%`} />
        <KpiCard label="Total Likes" value={totalLikes.toLocaleString()} />
      </div>
    );
  }

  if (props.platform === "instagram") {
    const { stats } = props;
    const totalReach = stats.reduce((a, p) => a + p.reach, 0);
    const totalLikes = stats.reduce((a, p) => a + p.like_count, 0);
    const totalSaves = stats.reduce((a, p) => a + p.saved, 0);
    const avgEng =
      stats.length > 0
        ? stats.reduce(
            (a, p) =>
              a +
              (p.reach > 0 ? ((p.like_count + p.comments_count + p.saved) / p.reach) * 100 : 0),
            0,
          ) / stats.length
        : 0;
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Reach" value={totalReach.toLocaleString()} />
        <KpiCard label="Total Saves" value={totalSaves.toLocaleString()} />
        <KpiCard label="Avg Engagement" value={`${avgEng.toFixed(2)}%`} />
        <KpiCard label="Total Likes" value={totalLikes.toLocaleString()} />
      </div>
    );
  }

  if (props.platform === "facebook") {
    const { stats } = props;
    const totalReach = stats.reduce((a, p) => a + p.reach, 0);
    const totalReactions = stats.reduce((a, p) => a + p.reactions, 0);
    const totalShares = stats.reduce((a, p) => a + p.shares_count, 0);
    const avgEng =
      stats.length > 0
        ? stats.reduce(
            (a, p) =>
              a +
              (p.reach > 0
                ? ((p.reactions + p.comments_count + p.shares_count) / p.reach) * 100
                : 0),
            0,
          ) / stats.length
        : 0;
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Reach" value={totalReach.toLocaleString()} />
        <KpiCard label="Total Reactions" value={totalReactions.toLocaleString()} />
        <KpiCard label="Avg Engagement" value={`${avgEng.toFixed(2)}%`} />
        <KpiCard label="Total Shares" value={totalShares.toLocaleString()} />
      </div>
    );
  }

  // overview (manual metrics)
  const { rows } = props;
  const totalViews = rows.reduce((a, r) => a + (r.views ?? 0), 0);
  const totalEng = rows.reduce(
    (a, r) => a + (r.likes ?? 0) + (r.comments ?? 0) + (r.shares ?? 0) + (r.saves ?? 0),
    0,
  );
  const follows = rows.reduce((a, r) => a + (r.follows_gained ?? 0), 0);
  const ctr = totalViews > 0 ? (totalEng / totalViews) * 100 : 0;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <KpiCard label="Total Views" value={totalViews.toLocaleString()} />
      <KpiCard label="Follows Gained" value={follows.toLocaleString()} />
      <KpiCard label="Total Engagement" value={totalEng.toLocaleString()} />
      <KpiCard label="Avg CTR" value={`${ctr.toFixed(2)}%`} />
    </div>
  );
}
