import { NextResponse } from "next/server";

const PAGE_ID = process.env.FACEBOOK_PAGE_ID!;
const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;

export async function POST(req: Request) {
  const { message, scheduled_at } = await req.json();
  if (!message?.trim()) return NextResponse.json({ error: "message required" }, { status: 400 });
  if (!PAGE_TOKEN) return NextResponse.json({ error: "FACEBOOK_PAGE_ACCESS_TOKEN not set" }, { status: 500 });

  const url = new URL(`https://graph.facebook.com/v25.0/${PAGE_ID}/feed`);
  url.searchParams.set("access_token", PAGE_TOKEN);

  const postBody: Record<string, unknown> = { message };
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
