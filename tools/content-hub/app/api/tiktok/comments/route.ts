import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

const TT_BASE = "https://open.tiktokapis.com/v2";

export async function GET(req: Request) {
  let token: string;
  try {
    token = await getToken("tiktok");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const videoIdParam = searchParams.get("video_id");

  let videoIds: string[];
  if (videoIdParam) {
    videoIds = [videoIdParam];
  } else {
    const listRes = await fetch(`${TT_BASE}/video/list/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=UTF-8",
      },
      body: JSON.stringify({ max_count: 5, fields: ["id"] }),
    });
    if (!listRes.ok) return NextResponse.json({ error: "Could not fetch video list" }, { status: 500 });
    const listJson = await listRes.json();
    videoIds = (listJson.data?.videos ?? []).map((v: { id: string }) => String(v.id));
  }

  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('tiktok', 'comment', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const videoId of videoIds) {
    const res = await fetch(`${TT_BASE}/research/video/comment/list/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=UTF-8",
      },
      body: JSON.stringify({
        video_id: videoId,
        max_count: 100,
        cursor: 0,
        fields: ["id", "text", "create_time", "like_count", "reply_count"],
      }),
    });
    if (!res.ok) continue;
    const json = await res.json();
    for (const c of json.data?.comments ?? []) {
      upsert.run(
        null,
        c.text ?? "",
        c.create_time ? new Date(c.create_time * 1000).toISOString() : new Date().toISOString(),
        String(c.id),
        videoId,
      );
      pulled++;
    }
  }

  return NextResponse.json({ pulled });
}
