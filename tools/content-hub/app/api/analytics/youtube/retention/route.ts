import { NextResponse } from "next/server";
import { getToken } from "@/lib/oauth-tokens";
import db from "@/lib/db";

const ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2/reports";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const videoId = searchParams.get("video_id");
  if (!videoId) {
    return NextResponse.json({ error: "video_id required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("youtube");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const stats = db
    .prepare("SELECT published_at FROM youtube_stats WHERE video_id = ?")
    .get(videoId) as { published_at: string | null } | undefined;
  const startDate = (stats?.published_at ?? "2024-01-01").slice(0, 10);
  const endDate = new Date().toISOString().slice(0, 10);

  const url = new URL(ANALYTICS_BASE);
  url.searchParams.set("ids", "channel==MINE");
  url.searchParams.set("startDate", startDate);
  url.searchParams.set("endDate", endDate);
  url.searchParams.set("metrics", "audienceWatchRatio,relativeRetentionPerformance");
  url.searchParams.set("dimensions", "elapsedVideoTimeRatio");
  url.searchParams.set("filters", `video==${videoId}`);
  url.searchParams.set("sort", "elapsedVideoTimeRatio");

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const detail = await res.text();
    return NextResponse.json(
      { error: "YouTube Analytics retention failed", status: res.status, detail },
      { status: res.status },
    );
  }

  const json = await res.json();
  // Rows shape: [[elapsedVideoTimeRatio, audienceWatchRatio, relativeRetentionPerformance], ...]
  const points = (json.rows ?? []).map((r: number[]) => ({
    t: r[0],
    watch_ratio: r[1],
    relative_perf: r[2],
  }));

  return NextResponse.json({ video_id: videoId, points });
}
