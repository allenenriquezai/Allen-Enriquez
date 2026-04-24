import { NextResponse } from "next/server";
import db from "@/lib/db";

const PAGE_ID = process.env.FACEBOOK_PAGE_ID!;
const PAGE_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN!;
const FB_BASE = "https://graph.facebook.com/v25.0";

export async function GET() {
  if (!PAGE_TOKEN) {
    return NextResponse.json({ error: "FACEBOOK_PAGE_ACCESS_TOKEN not set" }, { status: 500 });
  }
  const url = new URL(`${FB_BASE}/${PAGE_ID}/conversations`);
  url.searchParams.set("fields", "id,unread_count,messages{message,from,created_time}");
  url.searchParams.set("limit", "10");
  url.searchParams.set("access_token", PAGE_TOKEN);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "FB API failed", detail: await res.text() }, { status: 500 });
  }

  const json = await res.json();

  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('facebook', 'dm', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const convo of json.data ?? []) {
    for (const msg of convo.messages?.data ?? []) {
      upsert.run(
        msg.from?.name ?? null,
        msg.message ?? "",
        msg.created_time ?? new Date().toISOString(),
        msg.id,
        convo.id,
      );
      pulled++;
    }
  }

  return NextResponse.json({ pulled });
}
