"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { MetricRow } from "./metrics-table";

// Build a 30-day series. Y-axis is views. One line per platform.
export function MetricsChart({ rows }: { rows: MetricRow[] }) {
  const { data, platforms } = buildSeries(rows);
  if (!data.length) {
    return (
      <div className="h-64 border border-dashed border-border rounded-xl flex items-center justify-center text-sm text-muted-foreground">
        No metrics in the last 30 days.
      </div>
    );
  }
  const colors = ["#02B3E9", "#f59e0b", "#a855f7", "#22c55e", "#ef4444"];
  return (
    <div className="h-64 rounded-xl ring-1 ring-foreground/10 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis
            dataKey="date"
            stroke="rgba(255,255,255,0.5)"
            fontSize={11}
          />
          <YAxis stroke="rgba(255,255,255,0.5)" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: "#1b1b1b",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
            }}
          />
          <Legend />
          {platforms.map((p, i) => (
            <Line
              key={p}
              type="monotone"
              dataKey={p}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildSeries(rows: MetricRow[]): {
  data: Array<Record<string, number | string>>;
  platforms: string[];
} {
  const now = new Date();
  const days: string[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  const platformSet = new Set<string>();
  const byDay: Record<string, Record<string, number>> = {};
  for (const d of days) byDay[d] = {};
  for (const r of rows) {
    const day = (r.recorded_at || "").slice(0, 10);
    if (!byDay[day]) continue;
    const p = r.platform ?? "unknown";
    platformSet.add(p);
    byDay[day][p] = (byDay[day][p] ?? 0) + (r.views ?? 0);
  }
  const platforms = Array.from(platformSet);
  const data = days.map((d) => {
    const row: Record<string, number | string> = { date: d.slice(5) };
    for (const p of platforms) row[p] = byDay[d][p] ?? 0;
    return row;
  });
  return { data, platforms };
}
