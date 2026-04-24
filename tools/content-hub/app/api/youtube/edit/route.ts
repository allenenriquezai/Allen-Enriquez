import { NextResponse } from "next/server";
import { getToken } from "@/lib/oauth-tokens";

export async function PATCH(req: Request) {
  const { video_id, title, description, privacy } = await req.json();
  if (!video_id) {
    return NextResponse.json({ error: "video_id required" }, { status: 400 });
  }

  let token: string;
  try {
    token = await getToken("youtube");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 401 });
  }

  const currentRes = await fetch(
    `https://www.googleapis.com/youtube/v3/videos?id=${video_id}&part=snippet,status`,
    { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" },
  );
  if (!currentRes.ok) {
    return NextResponse.json({ error: "Could not fetch video", detail: await currentRes.text() }, { status: 500 });
  }
  const current = await currentRes.json();
  const item = current.items?.[0];
  if (!item) return NextResponse.json({ error: "Video not found" }, { status: 404 });

  const snippet = {
    ...item.snippet,
    ...(title !== undefined ? { title } : {}),
    ...(description !== undefined ? { description } : {}),
  };
  const status = {
    ...item.status,
    ...(privacy !== undefined ? { privacyStatus: privacy } : {}),
  };

  const res = await fetch(
    "https://www.googleapis.com/youtube/v3/videos?part=snippet,status",
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: video_id, snippet, status }),
    },
  );

  if (!res.ok) {
    return NextResponse.json({ error: "Update failed", detail: await res.text() }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
