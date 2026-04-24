import { NextResponse } from "next/server";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";
const RUPLOAD_BASE = "https://rupload.facebook.com/ig-api-upload/v25.0";

async function wait(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function pollStatus(mediaId: string): Promise<{ ok: boolean; detail?: string }> {
  let lastStatus = "";
  for (let i = 0; i < 18; i++) {
    await wait(10_000);
    const url = new URL(`${IG_BASE}/${mediaId}`);
    url.searchParams.set("fields", "status_code,status");
    url.searchParams.set("access_token", IG_TOKEN);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) continue;
    const json = await res.json();
    lastStatus = json.status || json.status_code || "";
    if (json.status_code === "FINISHED") return { ok: true };
    if (json.status_code === "ERROR") return { ok: false, detail: lastStatus };
  }
  return { ok: false, detail: `Timed out after 180s. Last status: ${lastStatus}` };
}

export async function POST(req: Request) {
  const { caption, media_url, media_type = "IMAGE", scheduled_at } = await req.json();
  if (!media_url?.trim()) {
    return NextResponse.json({ error: "media_url required" }, { status: 400 });
  }

  const isVideo = media_type !== "IMAGE";

  const containerUrl = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/media`);
  containerUrl.searchParams.set("access_token", IG_TOKEN);

  const containerBody: Record<string, string> = { media_type };
  if (caption) containerBody.caption = caption;
  if (scheduled_at) {
    containerBody.scheduled_publish_time = String(Math.floor(new Date(scheduled_at).getTime() / 1000));
  }
  if (isVideo) {
    containerBody.upload_type = "resumable";
  } else {
    containerBody.image_url = media_url;
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
  const containerJson = await containerRes.json();
  const creationId: string = containerJson.id;

  if (isVideo) {
    const mediaRes = await fetch(media_url, { cache: "no-store" });
    if (!mediaRes.ok) {
      return NextResponse.json(
        { error: "Failed to fetch media bytes from R2", detail: `${mediaRes.status} ${mediaRes.statusText}` },
        { status: 500 },
      );
    }
    const bytes = Buffer.from(await mediaRes.arrayBuffer());

    const uploadUrl = containerJson.uri || `${RUPLOAD_BASE}/${creationId}`;
    const uploadRes = await fetch(uploadUrl, {
      method: "POST",
      headers: {
        Authorization: `OAuth ${IG_TOKEN}`,
        offset: "0",
        file_size: String(bytes.length),
      },
      body: bytes,
      cache: "no-store",
    });
    if (!uploadRes.ok) {
      return NextResponse.json(
        { error: "Resumable upload failed", detail: await uploadRes.text() },
        { status: 500 },
      );
    }

    const { ok, detail } = await pollStatus(creationId);
    if (!ok) {
      return NextResponse.json(
        { error: "Video processing failed", detail: detail || "unknown" },
        { status: 500 },
      );
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
