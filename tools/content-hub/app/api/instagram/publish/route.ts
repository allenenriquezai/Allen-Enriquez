import { NextResponse } from "next/server";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

async function wait(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function pollStatus(mediaId: string): Promise<boolean> {
  for (let i = 0; i < 10; i++) {
    await wait(10_000);
    const url = new URL(`${IG_BASE}/${mediaId}`);
    url.searchParams.set("fields", "status_code");
    url.searchParams.set("access_token", IG_TOKEN);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) continue;
    const json = await res.json();
    if (json.status_code === "FINISHED") return true;
    if (json.status_code === "ERROR") return false;
  }
  return false;
}

export async function POST(req: Request) {
  const { caption, media_url, media_type = "IMAGE", scheduled_at } = await req.json();
  if (!media_url?.trim()) {
    return NextResponse.json({ error: "media_url required" }, { status: 400 });
  }

  const containerUrl = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/media`);
  containerUrl.searchParams.set("access_token", IG_TOKEN);

  const containerBody: Record<string, string> = { media_type };
  if (caption) containerBody.caption = caption;
  if (media_type === "IMAGE") {
    containerBody.image_url = media_url;
  } else {
    containerBody.video_url = media_url;
  }
  if (scheduled_at) {
    containerBody.scheduled_publish_time = String(Math.floor(new Date(scheduled_at).getTime() / 1000));
  }

  const containerRes = await fetch(containerUrl.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(containerBody),
    cache: "no-store",
  });
  if (!containerRes.ok) {
    return NextResponse.json(
      { error: "Container creation failed", detail: await containerRes.text() },
      { status: 500 },
    );
  }
  const { id: creationId } = await containerRes.json();

  if (media_type !== "IMAGE") {
    const ready = await pollStatus(creationId);
    if (!ready) {
      return NextResponse.json({ error: "Video processing timed out or failed" }, { status: 500 });
    }
  }

  const publishUrl = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/media_publish`);
  publishUrl.searchParams.set("access_token", IG_TOKEN);
  const publishRes = await fetch(publishUrl.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ creation_id: creationId }),
    cache: "no-store",
  });
  if (!publishRes.ok) {
    return NextResponse.json(
      { error: "Publish failed", detail: await publishRes.text() },
      { status: 500 },
    );
  }
  const { id: postId } = await publishRes.json();
  return NextResponse.json({ ok: true, post_id: postId });
}
