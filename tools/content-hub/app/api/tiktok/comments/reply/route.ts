import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

const TT_BASE = "https://open.tiktokapis.com/v2";

export async function POST(req: Request) {
  const { comment_id, video_id, text, inbox_id } = await req.json();
  if (!comment_id || !video_id || !text?.trim()) {
    return NextResponse.json({ error: "comment_id, video_id, and text required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("tiktok");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const res = await fetch(`${TT_BASE}/comment/publish/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
    },
    body: JSON.stringify({
      video_id,
      parent_comment_id: comment_id,
      text,
    }),
  });

  if (!res.ok) {
    return NextResponse.json({ error: "TikTok API failed", detail: await res.text() }, { status: 500 });
  }

  if (inbox_id) {
    db.prepare("UPDATE inbox SET reply_sent = 1, status = 'replied', reply_text = ? WHERE id = ?")
      .run(text, inbox_id);
  }

  return NextResponse.json({ ok: true });
}
