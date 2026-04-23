import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import db from "@/lib/db";

const execFileAsync = promisify(execFile);
const REPO_ROOT = path.resolve(process.cwd(), "../../..");
const SCRIPT = path.join(REPO_ROOT, "tools", "youtube_analytics.py");

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);

  if (searchParams.get("refresh") === "1") {
    try {
      await execFileAsync("python3", [SCRIPT], { timeout: 120_000 });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return NextResponse.json({ error: "Script failed", detail: msg }, { status: 500 });
    }
  }

  const rows = db
    .prepare(
      `SELECT video_id, title, url, published_at, views, likes, comments, fetched_at
       FROM youtube_stats
       ORDER BY published_at DESC
       LIMIT 50`
    )
    .all();

  return NextResponse.json({ stats: rows, count: rows.length });
}
