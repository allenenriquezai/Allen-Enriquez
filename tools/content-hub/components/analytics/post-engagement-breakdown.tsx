"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { FbPost, IgPost, TtStat } from "@/components/analytics/platform-tables";

type BreakdownData =
  | { platform: "tiktok"; post: TtStat }
  | { platform: "instagram"; post: IgPost }
  | { platform: "facebook"; post: FbPost };

interface PostEngagementBreakdownProps {
  data: BreakdownData;
  onClose: () => void;
}

export function PostEngagementBreakdown({ data, onClose }: PostEngagementBreakdownProps) {
  let title = "";
  let chartData: { metric: string; value: number }[] = [];
  let permalink: string | null = null;

  if (data.platform === "tiktok") {
    const p = data.post;
    title = p.title ?? p.video_id;
    chartData = [
      { metric: "Views", value: p.view_count },
      { metric: "Likes", value: p.like_count },
      { metric: "Comments", value: p.comment_count },
      { metric: "Shares", value: p.share_count },
    ];
  } else if (data.platform === "instagram") {
    const p = data.post;
    title = (p.caption ?? "(no caption)").slice(0, 60);
    permalink = p.permalink;
    chartData = [
      { metric: "Reach", value: p.reach },
      { metric: "Likes", value: p.like_count },
      { metric: "Comments", value: p.comments_count },
      { metric: "Saves", value: p.saved },
    ];
  } else {
    const p = data.post;
    title = (p.message ?? "(no caption)").slice(0, 60);
    permalink = p.permalink_url;
    chartData = [
      { metric: "Reach", value: p.reach },
      { metric: "Reactions", value: p.reactions },
      { metric: "Comments", value: p.comments_count },
      { metric: "Shares", value: p.shares_count },
    ];
  }

  return (
    <Card className="mt-2">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium truncate max-w-xs">
          {permalink ? (
            <a
              href={permalink}
              target="_blank"
              rel="noreferrer"
              className="hover:underline"
              style={{ color: "var(--brand)" }}
            >
              {title}
            </a>
          ) : (
            title
          )}
        </CardTitle>
        <Button size="sm" variant="ghost" onClick={onClose} className="shrink-0">✕</Button>
      </CardHeader>
      <CardContent>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 0, right: 24, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.08)"
                horizontal={false}
              />
              <XAxis type="number" stroke="rgba(255,255,255,0.5)" fontSize={11} />
              <YAxis
                type="category"
                dataKey="metric"
                stroke="rgba(255,255,255,0.5)"
                fontSize={11}
                width={72}
              />
              <Tooltip
                contentStyle={{
                  background: "#1b1b1b",
                  border: "1px solid rgba(255,255,255,0.15)",
                  fontSize: 12,
                }}
                formatter={(v) => [typeof v === "number" ? v.toLocaleString() : v, ""]}
              />
              <Bar
                dataKey="value"
                fill="#02B3E9"
                opacity={0.85}
                radius={[0, 3, 3, 0]}
                name="Value"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
