import { NextResponse } from "next/server";
import { getToken } from "@/lib/oauth-tokens";

const TT_BASE = "https://open.tiktokapis.com/v2";

export async function PATCH(req: Request) {
  const { video_id, title, description } = await req.json();
  if (!video_id?.trim()) {
    return NextResponse.json({ error: "video_id required" }, { status: 400 });
  }
  if (!title && !description) {
    return NextResponse.json({ error: "title or description required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("tiktok");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const body: Record<string, string> = { video_id };
  if (title) body.title = title;
  if (description) body.description = description;

  const res = await fetch(`${TT_BASE}/post/publish/video/update/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    return NextResponse.json({ error: "TikTok API failed", detail: await res.text() }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
