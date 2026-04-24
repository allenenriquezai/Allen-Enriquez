import { NextResponse } from "next/server";
import db from "@/lib/db";
import { getToken } from "@/lib/oauth-tokens";

export async function POST(req: Request) {
  const { parent_id, text, inbox_id } = await req.json();
  if (!parent_id || !text?.trim()) {
    return NextResponse.json({ error: "parent_id and text required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("youtube");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const res = await fetch(
    "https://www.googleapis.com/youtube/v3/comments?part=snippet",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        snippet: {
          parentId: parent_id,
          textOriginal: text,
        },
      }),
    },
  );

  if (!res.ok) {
    return NextResponse.json({ error: "YT API failed", detail: await res.text() }, { status: 500 });
  }

  const json = await res.json();
  if (inbox_id) {
    db.prepare("UPDATE inbox SET reply_sent = 1, status = 'replied', reply_text = ? WHERE id = ?")
      .run(text, inbox_id);
  }
  return NextResponse.json({ ok: true, comment_id: json.id });
}
