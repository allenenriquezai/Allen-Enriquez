"use client";

import { Badge } from "@/components/ui/badge";

export interface MetricRow {
  id: number;
  post_id: number | null;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  follows_gained: number;
  recorded_at: string;
  platform: string | null;
  asset_title: string | null;
  asset_type: string | null;
}

export function MetricsTable({ rows }: { rows: MetricRow[] }) {
  if (!rows.length) {
    return (
      <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-8 text-center">
        No metrics yet. Add one with the button above.
      </div>
    );
  }
  return (
    <div className="rounded-xl ring-1 ring-foreground/10 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-muted-foreground">
          <tr className="text-left">
            <th className="px-3 py-2 font-medium">Asset</th>
            <th className="px-3 py-2 font-medium">Platform</th>
            <th className="px-3 py-2 font-medium text-right">Views</th>
            <th className="px-3 py-2 font-medium text-right">Likes</th>
            <th className="px-3 py-2 font-medium text-right">Comments</th>
            <th className="px-3 py-2 font-medium text-right">Shares</th>
            <th className="px-3 py-2 font-medium text-right">Saves</th>
            <th className="px-3 py-2 font-medium text-right">Follows</th>
            <th className="px-3 py-2 font-medium">Recorded</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-border">
              <td className="px-3 py-2">
                {r.asset_title || `Post ${r.post_id ?? "—"}`}
              </td>
              <td className="px-3 py-2">
                <Badge variant="secondary">{r.platform ?? "—"}</Badge>
              </td>
              <td className="px-3 py-2 text-right font-mono">{r.views}</td>
              <td className="px-3 py-2 text-right font-mono">{r.likes}</td>
              <td className="px-3 py-2 text-right font-mono">{r.comments}</td>
              <td className="px-3 py-2 text-right font-mono">{r.shares}</td>
              <td className="px-3 py-2 text-right font-mono">{r.saves}</td>
              <td className="px-3 py-2 text-right font-mono">{r.follows_gained}</td>
              <td className="px-3 py-2 text-muted-foreground font-mono text-xs">
                {formatDate(r.recorded_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(s: string) {
  try {
    const d = new Date(s);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return s;
  }
}
