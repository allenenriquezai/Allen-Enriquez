import { NextResponse } from "next/server";
import db from "@/lib/db";

const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

export async function GET(req: Request) {
  if (!IG_TOKEN) {
    return NextResponse.json({ error: "INSTAGRAM_USER_TOKEN not set" }, { status: 500 });
  }
  const { searchParams } = new URL(req.url);
  const mediaIdParam = searchParams.get("media_id");
  const limit = searchParams.get("limit") ?? "25";

  let mediaIds: string[];
  if (mediaIdParam) {
    mediaIds = [mediaIdParam];
  } else {
    const rows = db
      .prepare("SELECT post_id FROM instagram_posts ORDER BY timestamp DESC LIMIT 10")
      .all() as { post_id: string }[];
    mediaIds = rows.map((r) => r.post_id);
  }

  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('instagram', 'comment', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const mediaId of mediaIds) {
    const url = new URL(`${IG_BASE}/${mediaId}/comments`);
    url.searchParams.set("fields", "id,text,username,timestamp");
    url.searchParams.set("limit", limit);
    url.searchParams.set("access_token", IG_TOKEN);

    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) continue;

    const json = await res.json();
    for (const c of json.data ?? []) {
      upsert.run(
        c.username ?? null,
        c.text ?? "",
        c.timestamp ?? new Date().toISOString(),
        c.id,
        mediaId,
      );
      pulled++;
    }
  }

  return NextResponse.json({ pulled });
}
