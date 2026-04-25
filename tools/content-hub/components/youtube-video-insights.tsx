"use client";

import * as React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";

type RetentionPoint = { t: number; watch_ratio: number; relative_perf: number };
type TrafficSource = {
  source: string;
  label: string;
  views: number;
  minutes_watched: number;
  avg_view_duration_sec: number;
};

export function YouTubeVideoInsights({
  videoId,
  title,
  onClose,
}: {
  videoId: string;
  title: string;
  onClose: () => void;
}) {
  const [retention, setRetention] = React.useState<RetentionPoint[] | null>(null);
  const [traffic, setTraffic] = React.useState<TrafficSource[] | null>(null);
  const [errR, setErrR] = React.useState<string | null>(null);
  const [errT, setErrT] = React.useState<string | null>(null);

  React.useEffect(() => {
    let alive = true;
    setRetention(null);
    setTraffic(null);
    setErrR(null);
    setErrT(null);

    fetch(`/api/analytics/youtube/retention?video_id=${videoId}`)
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        if (d.error) setErrR(d.detail ?? d.error);
        else setRetention(d.points ?? []);
      })
      .catch((e) => alive && setErrR(String(e)));

    fetch(`/api/analytics/youtube/traffic-sources?video_id=${videoId}`)
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        if (d.error) setErrT(d.detail ?? d.error);
        else setTraffic(d.sources ?? []);
      })
      .catch((e) => alive && setErrT(String(e)));

    return () => {
      alive = false;
    };
  }, [videoId]);

  return (
    <div className="rounded-lg border border-[color:var(--brand)]/40 bg-card p-4 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Insights
          </div>
          <div className="text-sm font-semibold">{title}</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Close ✕
        </button>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Retention curve
        </div>
        {errR && (
          <p className="text-xs text-amber-400">
            {errR}
            <br />
            <span className="text-muted-foreground">
              If 401/403: re-auth at <code>/api/youtube/auth</code> to grant <code>yt-analytics.readonly</code> scope.
            </span>
          </p>
        )}
        {!errR && retention === null && (
          <p className="text-xs text-muted-foreground">Loading…</p>
        )}
        {!errR && retention && retention.length === 0 && (
          <p className="text-xs text-muted-foreground">No retention data yet (video may need more views).</p>
        )}
        {!errR && retention && retention.length > 0 && (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={retention.map((p) => ({ ...p, pct: Math.round(p.t * 100) }))}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="pct" tick={{ fontSize: 10 }} unit="%" />
                <YAxis tick={{ fontSize: 10 }} domain={[0, "auto"]} />
                <Tooltip
                  formatter={(v) => (typeof v === "number" ? v.toFixed(2) : String(v))}
                  labelFormatter={(l) => `${l}% through video`}
                />
                <Line
                  type="monotone"
                  dataKey="watch_ratio"
                  stroke="var(--brand)"
                  strokeWidth={2}
                  dot={false}
                  name="Audience watch ratio"
                />
                <Line
                  type="monotone"
                  dataKey="relative_perf"
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  name="Relative perf"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Traffic sources
        </div>
        {errT && (
          <p className="text-xs text-amber-400">{errT}</p>
        )}
        {!errT && traffic === null && (
          <p className="text-xs text-muted-foreground">Loading…</p>
        )}
        {!errT && traffic && traffic.length === 0 && (
          <p className="text-xs text-muted-foreground">No traffic source data yet.</p>
        )}
        {!errT && traffic && traffic.length > 0 && (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={traffic} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="label"
                  tick={{ fontSize: 10 }}
                  width={140}
                />
                <Tooltip />
                <Bar dataKey="views" fill="var(--brand)" name="Views" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
