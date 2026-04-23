import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { execFile } from "node:child_process";
import path from "node:path";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const REPO_ROOT = path.resolve(process.cwd(), "../../..");

const SYSTEM_PROMPT = `You adapt a video transcript into a short-form reel script for Allen, an AI automation consultant in Brisbane AU.

Brand voice: direct, honest, proof-first. No hype. Real results from real work.
Audience: small business owners, VAs, semi-technical professionals.

Script structure:
- Hook (1 sentence, grabs attention)
- Explain (1–2 sentences, what and why)
- Illustrate (1–2 sentences, specific real example — Allen must personalise this)
- Takeaway (1 sentence)

Constraints:
- 80–120 words total
- No buzzwords ("game-changer", "revolutionary", "unlock")
- Adapt the insight + structure — do NOT copy the creator's specific story verbatim

Also write 3–4 "edits needed" bullets telling Allen exactly what to replace with his own story/results.

Return STRICT JSON (no markdown, no prose outside JSON):
{
  "hook": "<first sentence — the hook>",
  "body": "<full 80–120 word reel script>",
  "edits_needed": "• bullet 1\\n• bullet 2\\n• bullet 3"
}`;

function runImportScript(url: string): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const script = path.join(REPO_ROOT, "tools", "import_link.py");
    execFile(
      "python3",
      [script, url],
      {
        cwd: REPO_ROOT,
        timeout: 10 * 60 * 1000,
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

export async function POST(req: Request) {
  let body: { url?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const url = (body.url ?? "").trim();
  if (!url || !url.startsWith("http")) {
    return NextResponse.json({ error: "valid url required" }, { status: 400 });
  }

  // Run Python script to fetch + transcribe
  let pyOut: Record<string, string | number>;
  try {
    const { stdout } = await runImportScript(url);
    pyOut = JSON.parse(stdout.trim());
  } catch (err) {
    const e = err as { message?: string; stderr?: string };
    console.error("[import-link] python failed:", e.stderr ?? e.message);
    return NextResponse.json({ error: e.message ?? "script failed" }, { status: 500 });
  }

  if (pyOut.error) {
    return NextResponse.json({ error: pyOut.error }, { status: 422 });
  }

  const { title, creator, platform, transcript, source_url, duration_sec } = pyOut as {
    title: string;
    creator: string;
    platform: string;
    transcript: string;
    source_url: string;
    duration_sec: number;
  };

  // Claude: rewrite + edits needed
  const userPrompt = `CREATOR: ${creator}
PLATFORM: ${platform}
TITLE: ${title}
DURATION: ${duration_sec}s
TRANSCRIPT:
${transcript || "(no transcript — write a reel based on the title alone)"}`;

  let hook = "";
  let reelBody = "";
  let editsNeeded = "";

  try {
    const msg = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 600,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userPrompt }],
    });
    const raw = msg.content[0].type === "text" ? msg.content[0].text.trim() : "{}";
    // Strip code fences if model added them
    const cleaned = raw.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
    const parsed = JSON.parse(cleaned);
    hook = parsed.hook ?? "";
    reelBody = parsed.body ?? "";
    editsNeeded = parsed.edits_needed ?? "";
  } catch (err) {
    console.error("[import-link] claude failed:", err);
    // Fallback: use transcript as body
    reelBody = transcript.slice(0, 600);
  }

  const notes = editsNeeded
    ? `EDITS NEEDED:\n${editsNeeded}\n\n--- ORIGINAL TRANSCRIPT ---\n${transcript}`
    : `--- ORIGINAL TRANSCRIPT ---\n${transcript}`;

  const wordCount = reelBody.split(/\s+/).filter(Boolean).length;

  // Insert idea
  const ideaResult = db
    .prepare(
      `INSERT INTO ideas (title, hook, status, notes, source_url, source_platform, modeled_after, batch)
       VALUES (?, ?, 'needs_edit', ?, ?, ?, ?, 'imported_link')`,
    )
    .run(title, hook || null, notes, source_url, platform, creator || null);

  const ideaId = ideaResult.lastInsertRowid as number;

  // Insert reel script
  const scriptResult = db
    .prepare(
      `INSERT INTO scripts (idea_id, variant, body, word_count) VALUES (?, 'reel', ?, ?)`,
    )
    .run(ideaId, reelBody, wordCount);

  const scriptId = scriptResult.lastInsertRowid as number;

  return NextResponse.json({
    idea: {
      ideaId,
      title,
      hook: hook || null,
      pillar: null,
      status: "needs_edit",
      notes,
      scriptId,
      reelBody,
      hasCarousel: false,
      modeledAfter: creator || null,
    },
  });
}
