import { NextResponse } from "next/server";
import db from "@/lib/db";

const CHANNEL_ID = "UCbxyZe-sodJxfgQzj1qoAcA"; // @allenenriquezz
const YT_BASE = "https://www.googleapis.com/youtube/v3";

async function ytFetch(path: string, params: Record<string, string>) {
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error("YOUTUBE_API_KEY not set");
  const url = new URL(`${YT_BASE}${path}`);
  url.searchParams.set("key", apiKey);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`YouTube API ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function refreshYouTubeStats() {
  // 1. Get uploads playlist ID
  const chRes = await ytFetch("/channels", { id: CHANNEL_ID, part: "contentDetails" });
  const uploadsId: string = chRes.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
  if (!uploadsId) throw new Error("No uploads playlist found");

  // 2. Collect video IDs from playlist
  const videoIds: string[] = [];
  let pageToken: string | undefined;
  do {
    const params: Record<string, string> = {
      playlistId: uploadsId,
      maxResults: "50",
      part: "contentDetails",
    };
    if (pageToken) params.pageToken = pageToken;
    const plRes = await ytFetch("/playlistItems", params);
    for (const item of plRes.items ?? []) {
      const id = item.contentDetails?.videoId;
      if (id) videoIds.push(id);
    }
    pageToken = plRes.nextPageToken;
  } while (pageToken && videoIds.length < 50);

  if (!videoIds.length) return 0;

  // 3. Fetch stats in batches of 50
  const chunks: string[][] = [];
  for (let i = 0; i < videoIds.length; i += 50) chunks.push(videoIds.slice(i, i + 50));

  const upsert = db.prepare(`
    INSERT INTO youtube_stats (video_id, title, url, published_at, views, likes, comments, fetched_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(video_id) DO UPDATE SET
      title=excluded.title, views=excluded.views, likes=excluded.likes,
      comments=excluded.comments, fetched_at=excluded.fetched_at
  `);

  let count = 0;
  const now = new Date().toISOString();
  for (const chunk of chunks) {
    const vRes = await ytFetch("/videos", { id: chunk.join(","), part: "snippet,statistics" });
    for (const v of vRes.items ?? []) {
      upsert.run(
        v.id,
        v.snippet.title,
        `https://www.youtube.com/watch?v=${v.id}`,
        v.snippet.publishedAt,
        parseInt(v.statistics.viewCount ?? "0", 10),
        parseInt(v.statistics.likeCount ?? "0", 10),
        parseInt(v.statistics.commentCount ?? "0", 10),
        now,
      );
      count++;
    }
  }
  return count;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);

  if (searchParams.get("refresh") === "1") {
    try {
      await refreshYouTubeStats();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return NextResponse.json({ error: "Refresh failed", detail: msg }, { status: 500 });
    }
  }

  const rows = db
    .prepare(
      `SELECT video_id, title, url, published_at, views, likes, comments, fetched_at
       FROM youtube_stats
       ORDER BY published_at DESC
       LIMIT 50`,
    )
    .all();

  return NextResponse.json({ stats: rows, count: rows.length });
}
