import { NextResponse } from "next/server";
import db from "@/lib/db";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

export async function POST(req: Request) {
  const { thread_id, message, inbox_id } = await req.json();
  if (!thread_id || !message?.trim()) {
    return NextResponse.json({ error: "thread_id and message required" }, { status: 400 });
  }
  const url = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/messages`);
  url.searchParams.set("access_token", IG_TOKEN);
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipient: { thread_id }, message: { text: message } }),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "IG API failed", detail: await res.text() }, { status: 500 });
  }
  if (inbox_id) {
    db.prepare("UPDATE inbox SET reply_sent = 1, status = 'replied', reply_text = ? WHERE id = ?")
      .run(message, inbox_id);
  }
  return NextResponse.json({ ok: true });
}
