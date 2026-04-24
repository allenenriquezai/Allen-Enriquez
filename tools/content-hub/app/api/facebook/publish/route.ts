import { NextResponse } from "next/server";

const PAGE_ID = process.env.FACEBOOK_PAGE_ID!;
const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;

export async function POST(req: Request) {
  const { message, media_url, media_type, scheduled_at } = await req.json();
  if (!message?.trim() && !media_url) {
    return NextResponse.json({ error: "message or media_url required" }, { status: 400 });
  }
  if (!PAGE_TOKEN) return NextResponse.json({ error: "FACEBOOK_PAGE_ACCESS_TOKEN not set" }, { status: 500 });

  const isVideo = media_url && (media_type === "video" || /\.(mp4|mov|m4v)(\?|$)/i.test(media_url));
  const endpoint = isVideo ? "videos" : "feed";
  const url = new URL(`https://graph.facebook.com/v25.0/${PAGE_ID}/${endpoint}`);
  url.searchParams.set("access_token", PAGE_TOKEN);

  const postBody: Record<string, unknown> = {};
  if (isVideo) {
    postBody.file_url = media_url;
    if (message) postBody.description = message;
  } else {
    if (message) postBody.message = message;
    if (media_url) postBody.link = media_url;
  }
  if (scheduled_at) {
    const ts = Math.floor(new Date(scheduled_at).getTime() / 1000);
    postBody.scheduled_publish_time = ts;
    postBody.published = false;
  }

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(postBody),
  });

  if (!res.ok) {
    const err = await res.text();
    return NextResponse.json({ error: "FB API error", detail: err }, { status: 502 });
  }

  return NextResponse.json({ ok: true, result: await res.json() });
}
