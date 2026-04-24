import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

const TT_BASE = "https://open.tiktokapis.com/v2";

async function wait(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function pollPublishStatus(publishId: string, token: string): Promise<boolean> {
  for (let i = 0; i < 15; i++) {
    await wait(10_000);
    const res = await fetch(`${TT_BASE}/post/publish/status/fetch/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=UTF-8",
      },
      body: JSON.stringify({ publish_id: publishId }),
    });
    if (!res.ok) continue;
    const json = await res.json();
    const status = json.data?.status;
    if (status === "PUBLISH_COMPLETE") return true;
    if (status === "FAILED") return false;
  }
  return false;
}

export async function POST(req: Request) {
  const { title, media_url, privacy = "PUBLIC_TO_EVERYONE", schedule_id, scheduled_at } = await req.json();

  if (!title?.trim() || !media_url?.trim()) {
    return NextResponse.json({ error: "title and media_url required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("tiktok");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  // Fetch video metadata
  const headRes = await fetch(media_url, { method: "HEAD" });
  const videoSize = parseInt(headRes.headers.get("content-length") ?? "0", 10);

  // Step 1: Init upload
  const initRes = await fetch(`${TT_BASE}/post/publish/video/init/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
    },
    body: JSON.stringify({
      post_info: {
        title,
        privacy_level: privacy,
        disable_duet: false,
        disable_comment: false,
        disable_stitch: false,
        ...(scheduled_at ? { schedule_time: Math.floor(new Date(scheduled_at).getTime() / 1000) } : {}),
      },
      source_info: {
        source: "PULL_FROM_URL",
        video_url: media_url,
        video_size: videoSize,
      },
    }),
  });

  if (!initRes.ok) {
    return NextResponse.json(
      { error: "TikTok upload init failed", detail: await initRes.text() },
      { status: 500 },
    );
  }

  const initData = await initRes.json();
  const publishId = initData.data?.publish_id;
  if (!publishId) {
    return NextResponse.json({ error: "No publish_id returned", detail: JSON.stringify(initData) }, { status: 500 });
  }

  // Step 2: Poll for completion
  const success = await pollPublishStatus(publishId, token);
  if (!success) {
    return NextResponse.json({ error: "TikTok publish timed out or failed", publish_id: publishId }, { status: 500 });
  }

  if (schedule_id) {
    db.prepare("UPDATE schedule SET status = 'posted' WHERE id = ?").run(schedule_id);
  }

  return NextResponse.json({ ok: true, publish_id: publishId });
}
