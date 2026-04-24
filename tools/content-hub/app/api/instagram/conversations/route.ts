import { NextResponse } from "next/server";
import db from "@/lib/db";

const IG_ACCOUNT_ID = process.env.INSTAGRAM_ACCOUNT_ID!;
const IG_TOKEN = process.env.INSTAGRAM_USER_TOKEN!;
const IG_BASE = "https://graph.facebook.com/v25.0";

export async function GET() {
  if (!IG_TOKEN) {
    return NextResponse.json({ error: "INSTAGRAM_USER_TOKEN not set" }, { status: 500 });
  }
  const url = new URL(`${IG_BASE}/${IG_ACCOUNT_ID}/conversations`);
  url.searchParams.set("fields", "id,messages{id,text,from,created_time}");
  url.searchParams.set("limit", "10");
  url.searchParams.set("access_token", IG_TOKEN);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "IG API failed", detail: await res.text() }, { status: 500 });
  }

  const json = await res.json();
  const upsert = db.prepare(`
    INSERT INTO inbox (platform, thread_type, author, thread_text, received_at, external_id, post_id, status)
    VALUES ('instagram', 'dm', ?, ?, ?, ?, ?, 'new')
    ON CONFLICT(platform, external_id) WHERE external_id IS NOT NULL DO NOTHING
  `);

  let pulled = 0;
  for (const convo of json.data ?? []) {
    for (const msg of convo.messages?.data ?? []) {
      upsert.run(
        msg.from?.username ?? msg.from?.name ?? null,
        msg.text ?? "",
        msg.created_time ?? new Date().toISOString(),
        msg.id,
        convo.id,
      );
      pulled++;
    }
  }
  return NextResponse.json({ pulled });
}
