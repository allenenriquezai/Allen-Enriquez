import { NextResponse } from "next/server";
import db from "@/lib/db";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_BASE = "https://graph.facebook.com/v25.0";
const RUPLOAD_BASE = "https://rupload.facebook.com/ig-api-upload/v25.0";

/**
 * Resolve the IG access token. Prefer the DB row (kept fresh by
 * /api/instagram/refresh-token). Fall back to env on cold start.
 * Emits a console.warn if the stored token is <14 days from expiry.
 */
function getIgToken(): string {
  try {
    const row = db
      .prepare(
        "SELECT access_token, expires_at FROM oauth_tokens WHERE platform = ?",
      )
      .get("instagram") as
      | { access_token: string; expires_at: string | null }
      | undefined;

    if (row?.access_token) {
      if (row.expires_at) {
        const days = Math.floor(
          (new Date(row.expires_at).getTime() - Date.now()) /
            (24 * 60 * 60 * 1000),
        );
        if (days < 14) {
          console.warn(
            `[ig-publish] IG token expires in ${days} days (${row.expires_at}). Trigger /api/instagram/refresh-token.`,
          );
        }
      }
      return row.access_token;
    }
  } catch (err) {
    console.warn("[ig-publish] oauth_tokens read failed, falling back to env:", err);
  }
  return process.env.INSTAGRAM_USER_TOKEN!;
}

async function wait(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function pollStatus(mediaId: string, token: string): Promise<{ ok: boolean; detail?: string }> {
  let lastStatus = "";
  for (let i = 0; i < 18; i++) {
    await wait(10_000);
    const url = new URL(`${IG_BASE}/${mediaId}`);
    url.searchParams.set("fields", "status_code,status");
    url.searchParams.set("access_token", token);
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
  const IG_TOKEN = getIgToken();

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

    const { ok, detail } = await pollStatus(creationId, IG_TOKEN);
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
