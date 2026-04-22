import { NextResponse } from "next/server";
import db from "@/lib/db";

// GET /api/inbox?platform=X&thread_type=Y&status=Z
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const platform = searchParams.get("platform");
  const threadType = searchParams.get("thread_type");
  const status = searchParams.get("status");

  const where: string[] = [];
  const params: unknown[] = [];
  if (platform && platform !== "all") {
    where.push("platform = ?");
    params.push(platform);
  }
  if (threadType && threadType !== "all") {
    where.push("thread_type = ?");
    params.push(threadType);
  }
  if (status && status !== "all") {
    where.push("status = ?");
    params.push(status);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const rows = db
    .prepare(
      `SELECT * FROM inbox ${whereSql} ORDER BY datetime(received_at) DESC, id DESC`,
    )
    .all(...params);
  return NextResponse.json({ messages: rows });
}

// POST /api/inbox
export async function POST(req: Request) {
  let body: {
    platform?: string;
    thread_type?: string;
    author?: string;
    thread_text?: string;
    received_at?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  if (!body.platform || !body.thread_text) {
    return NextResponse.json(
      { error: "platform and thread_text required" },
      { status: 400 },
    );
  }
  const info = db
    .prepare(
      `INSERT INTO inbox (platform, thread_type, author, thread_text, received_at)
       VALUES (@platform, @thread_type, @author, @thread_text, COALESCE(@received_at, CURRENT_TIMESTAMP))`,
    )
    .run({
      platform: body.platform,
      thread_type: body.thread_type ?? "comment",
      author: body.author ?? null,
      thread_text: body.thread_text,
      received_at: body.received_at ?? null,
    });
  const row = db
    .prepare(`SELECT * FROM inbox WHERE id = ?`)
    .get(Number(info.lastInsertRowid));
  return NextResponse.json({ ok: true, message: row });
}
