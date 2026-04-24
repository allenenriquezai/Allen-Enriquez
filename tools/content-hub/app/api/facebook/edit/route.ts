import { NextResponse } from "next/server";

const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;
const FB_BASE = "https://graph.facebook.com/v25.0";

export async function PATCH(req: Request) {
  const { post_id, message } = await req.json();
  if (!post_id || !message?.trim()) {
    return NextResponse.json({ error: "post_id and message required" }, { status: 400 });
  }
  const url = new URL(`${FB_BASE}/${post_id}`);
  url.searchParams.set("access_token", PAGE_TOKEN);
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "FB API failed", detail: await res.text() }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
