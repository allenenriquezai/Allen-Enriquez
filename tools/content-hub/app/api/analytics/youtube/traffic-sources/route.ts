import { NextResponse } from "next/server";
import { getToken } from "@/lib/oauth-tokens";
import db from "@/lib/db";

const ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2/reports";

const SOURCE_LABELS: Record<string, string> = {
  ADVERTISING: "Ads",
  ANNOTATION: "Annotations",
  CAMPAIGN_CARD: "Campaign card",
  END_SCREEN: "End screen",
  EXT_URL: "External link",
  HASHTAGS: "Hashtags",
  LIVE: "Live stream",
  NOTIFICATION: "Notifications",
  NO_LINK_EMBEDDED: "Embedded (no link)",
  NO_LINK_OTHER: "Other (no link)",
  PLAYLIST: "Playlist",
  PROMOTED: "Promoted",
  RELATED_VIDEO: "Suggested videos",
  SHORTS: "Shorts feed",
  SHORTS_CONTENT_LINKS: "Shorts content links",
  SOUND_PAGE: "Shorts sound page",
  SUBSCRIBER: "Subscriber feed",
  YT_CHANNEL: "Channel page",
  YT_OTHER_PAGE: "Other YT page",
  YT_PLAYLIST_PAGE: "Playlist page",
  YT_SEARCH: "YT search",
};

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
  url.searchParams.set("metrics", "views,estimatedMinutesWatched,averageViewDuration");
  url.searchParams.set("dimensions", "insightTrafficSourceType");
  url.searchParams.set("filters", `video==${videoId}`);
  url.searchParams.set("sort", "-views");

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const detail = await res.text();
    return NextResponse.json(
      { error: "YouTube Analytics traffic-sources failed", status: res.status, detail },
      { status: res.status },
    );
  }

  const json = await res.json();
  const sources = (json.rows ?? []).map(
    (r: [string, number, number, number]) => ({
      source: r[0],
      label: SOURCE_LABELS[r[0]] ?? r[0],
      views: r[1],
      minutes_watched: r[2],
      avg_view_duration_sec: r[3],
    }),
  );

  return NextResponse.json({ video_id: videoId, sources });
}
