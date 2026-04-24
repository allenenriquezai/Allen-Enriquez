import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

const YT_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos";

export async function POST(req: Request) {
  const {
    title,
    description = "",
    media_url,
    privacy = "public",
    schedule_id,
    scheduled_at,
  } = await req.json();

  if (!title?.trim() || !media_url?.trim()) {
    return NextResponse.json({ error: "title and media_url required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("youtube");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const videoRes = await fetch(media_url);
  if (!videoRes.ok || !videoRes.body) {
    return NextResponse.json({ error: "Could not fetch video from media_url" }, { status: 400 });
  }

  const contentType = videoRes.headers.get("content-type") ?? "video/mp4";
  const contentLength = videoRes.headers.get("content-length");

  const metadata = {
    snippet: { title, description, categoryId: "22" },
    status: {
      privacyStatus: scheduled_at ? "private" : privacy,
      ...(scheduled_at ? { publishAt: new Date(scheduled_at).toISOString() } : {}),
    },
  };

  const initRes = await fetch(`${YT_UPLOAD}?uploadType=resumable&part=snippet,status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Upload-Content-Type": contentType,
      ...(contentLength ? { "X-Upload-Content-Length": contentLength } : {}),
    },
    body: JSON.stringify(metadata),
  });

  if (!initRes.ok) {
    return NextResponse.json(
      { error: "Upload init failed", detail: await initRes.text() },
      { status: 500 },
    );
  }

  const uploadUrl = initRes.headers.get("location");
  if (!uploadUrl) {
    return NextResponse.json({ error: "No upload URL returned" }, { status: 500 });
  }

  const uploadRes = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": contentType,
      ...(contentLength ? { "Content-Length": contentLength } : {}),
    },
    body: videoRes.body,
    // @ts-expect-error — Next.js Node runtime supports duplex streaming
    duplex: "half",
  });

  if (!uploadRes.ok) {
    return NextResponse.json(
      { error: "Upload failed", detail: await uploadRes.text() },
      { status: 500 },
    );
  }

  const video = await uploadRes.json();

  if (schedule_id) {
    db.prepare("UPDATE schedule SET status = 'posted' WHERE id = ?").run(schedule_id);
  }

  return NextResponse.json({
    ok: true,
    video_id: video.id,
    url: `https://youtube.com/watch?v=${video.id}`,
  });
}
