import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import path from "node:path";
import db from "@/lib/db";

// POST /api/creator-feed/refresh
//
// Spawns `python3 tools/creator_feed.py --no-transcribe --no-breakdown`
// (metadata-only, fast) from the repo root, waits for it to exit, then
// returns the counts parsed from its stdout + the current DB total.
//
// Query params:
//   ?transcribe=1     — include audio download + whisper (slow)
//   ?breakdown=1      — include Claude summary (costs ~$0.005/post)
//   ?limit=N          — override max_posts_per_run
//   ?creator=<name>   — filter to one creator
//
// Returns: { ok, added, total, stdout, stderr }

const REPO_ROOT = path.resolve(process.cwd(), "../../..");

export async function POST(req: Request) {
  const { searchParams } = new URL(req.url);

  const args: string[] = [];
  const limit = searchParams.get("limit");
  const creator = searchParams.get("creator");
  if (!searchParams.has("transcribe")) args.push("--no-transcribe");
  if (!searchParams.has("breakdown")) args.push("--no-breakdown");
  if (limit) args.push("--limit", limit);
  if (creator) args.push("--creator", creator);

  try {
    const { stdout, stderr } = await runScript(args);

    // Parse added count from machine-readable line: CREATOR_FEED_ADDED=N
    const match = stdout.match(/CREATOR_FEED_ADDED=(\d+)/);
    const added = match ? Number(match[1]) : null;

    const totalRow = db
      .prepare("SELECT COUNT(*) AS n FROM creator_posts")
      .get() as { n: number };

    return NextResponse.json({
      ok: true,
      added,
      total: totalRow.n,
      stdout: stdout.slice(-4000),   // cap to avoid huge payloads
      stderr: stderr.slice(-2000),
    });
  } catch (err) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    console.error("[creator-feed/refresh] failed:", e.stderr ?? e.message);
    return NextResponse.json(
      {
        ok: false,
        error: e.message ?? "script failed",
        stdout: (e.stdout ?? "").slice(-4000),
        stderr: (e.stderr ?? "").slice(-2000),
      },
      { status: 500 },
    );
  }
}

function runScript(
  args: string[],
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const script = path.join(REPO_ROOT, "tools", "creator_feed.py");
    execFile(
      "python3",
      [script, ...args],
      {
        cwd: REPO_ROOT,
        timeout: 5 * 60 * 1000, // 5 min — metadata-only is usually <30s
        maxBuffer: 10 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (error) {
          reject(Object.assign(error, { stdout, stderr }));
        } else {
          resolve({ stdout, stderr });
        }
      },
    );
  });
}
