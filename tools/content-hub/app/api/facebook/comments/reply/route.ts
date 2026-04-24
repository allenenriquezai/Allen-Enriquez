import { NextResponse } from "next/server";
import db from "@/lib/db";

const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;
const FB_BASE = "https://graph.facebook.com/v25.0";

export async function POST(req: Request) {
  const { comment_id, message, inbox_id } = await req.json();
  if (!comment_id || !message?.trim()) {
    return NextResponse.json({ error: "comment_id and message required" }, { status: 400 });
  }
  const url = new URL(`${FB_BASE}/${comment_id}/comments`);
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
  const json = await res.json();
  if (inbox_id) {
    db.prepare("UPDATE inbox SET reply_sent = 1, status = 'replied', reply_text = ? WHERE id = ?")
      .run(message, inbox_id);
  }
  return NextResponse.json({ ok: true, reply_id: json.id });
}
