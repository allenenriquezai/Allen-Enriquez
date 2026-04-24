import { NextResponse } from "next/server";
import db from "@/lib/db";

const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;
const FB_BASE = "https://graph.facebook.com/v25.0";

export async function GET() {
  if (!PAGE_TOKEN) {
    return NextResponse.json({ error: "FACEBOOK_PAGE_ACCESS_TOKEN not set" }, { status: 500 });
  }

  const posts = db
    .prepare("SELECT post_id FROM facebook_posts ORDER BY created_time DESC LIMIT 25")
    .all() as { post_id: string }[];

  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('facebook', 'comment', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const { post_id } of posts) {
    const url = new URL(`${FB_BASE}/${post_id}/comments`);
    url.searchParams.set("fields", "id,message,from,created_time");
    url.searchParams.set("limit", "25");
    url.searchParams.set("access_token", PAGE_TOKEN);

    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) continue;

    const json = await res.json();
    for (const c of json.data ?? []) {
      upsert.run(
        c.from?.name ?? null,
        c.message ?? "",
        c.created_time ?? new Date().toISOString(),
        c.id,
        post_id,
      );
      pulled++;
    }
  }

  return NextResponse.json({ pulled });
}
