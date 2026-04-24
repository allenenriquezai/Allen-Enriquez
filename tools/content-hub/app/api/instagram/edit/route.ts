import { NextResponse } from "next/server";

const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

export async function PATCH(req: Request) {
  const { post_id, caption } = await req.json();
  if (!post_id || !caption?.trim()) {
    return NextResponse.json({ error: "post_id and caption required" }, { status: 400 });
  }
  const url = new URL(`${IG_BASE}/${post_id}`);
  url.searchParams.set("access_token", IG_TOKEN);
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ caption }),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "IG API failed", detail: await res.text() }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
