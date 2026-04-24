import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

export async function GET(req: Request) {
  let token: string;
  try {
    token = await getToken("youtube");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const videoIdParam = searchParams.get("video_id");
  const maxResults = searchParams.get("limit") ?? "50";

  let videoIds: string[];
  if (videoIdParam) {
    videoIds = [videoIdParam];
  } else {
    const rows = db
      .prepare("SELECT video_id FROM youtube_stats ORDER BY published_at DESC LIMIT 5")
      .all() as { video_id: string }[];
    videoIds = rows.map((r) => r.video_id);
  }

  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('youtube', 'comment', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const videoId of videoIds) {
    const url = new URL("https://www.googleapis.com/youtube/v3/commentThreads");
    url.searchParams.set("videoId", videoId);
    url.searchParams.set("part", "snippet");
    url.searchParams.set("maxResults", maxResults);

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) continue;

    const json = await res.json();
    for (const thread of json.items ?? []) {
      const top = thread.snippet?.topLevelComment?.snippet;
      if (!top) continue;
      upsert.run(
        top.authorDisplayName ?? null,
        top.textOriginal ?? top.textDisplay ?? "",
        top.publishedAt ?? new Date().toISOString(),
        thread.id,
        videoId,
      );
      pulled++;
    }
  }

  return NextResponse.json({ pulled });
}
