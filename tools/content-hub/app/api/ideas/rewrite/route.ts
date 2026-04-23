import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You rewrite short-form video scripts for Allen, an AI automation consultant.

Brand voice: direct, honest, proof-first. Not hype. Real results from real work.
Audience: small business owners, VAs, semi-technical professionals.

Script structure:
- Hook (1 sentence, grabs attention — use cheat-code / steal-my-system / before-after formulas)
- Explain (1–2 sentences, what and why)
- Illustrate (1–2 sentences, specific real example from Allen's work)
- Takeaway (1 sentence, what to do or think)

Constraints:
- 80–120 words total (60–90 second reel)
- No buzzwords or empty hype ("game-changer", "revolutionary", "unlock your potential")
- Incorporate the Notes field as specific feedback — this is what needs to change

Return ONLY the rewritten script body, no preamble or commentary.`;

type Row = { title: string; hook: string | null; notes: string | null; body: string | null; script_id: number | null };

export async function POST(req: Request) {
  let body: { idea_ids?: number[] };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const ids = body.idea_ids;
  if (!Array.isArray(ids) || ids.length === 0) {
    return NextResponse.json({ error: "idea_ids required" }, { status: 400 });
  }

  const placeholders = ids.map(() => "?").join(",");
  const rows = db
    .prepare(
      `SELECT i.id AS idea_id, i.title, i.hook, i.notes,
              s.id AS script_id, s.body
       FROM ideas i
       LEFT JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
       WHERE i.id IN (${placeholders})`,
    )
    .all(...ids) as Array<{ idea_id: number } & Row>;

  const results: Array<{ id: number; title: string; body: string; word_count: number }> = [];

  for (const row of rows) {
    const userPrompt = `Title: ${row.title}
Hook: ${row.hook ?? "(none)"}
Notes / feedback: ${row.notes?.trim() || "(none — just improve clarity and pacing)"}

Current script:
${row.body?.trim() || "(no script yet — write one from scratch based on the title and hook)"}`;

    try {
      const msg = await client.messages.create({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 512,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userPrompt }],
      });

      const newBody = msg.content[0].type === "text" ? msg.content[0].text.trim() : "";
      const wordCount = newBody.split(/\s+/).filter(Boolean).length;

      if (row.script_id) {
        db.prepare("UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
          .run(newBody, wordCount, row.script_id);
      } else {
        db.prepare("INSERT INTO scripts (idea_id, variant, body, word_count) VALUES (?, 'reel', ?, ?)")
          .run(row.idea_id, newBody, wordCount);
      }

      results.push({ id: row.idea_id, title: row.title, body: newBody, word_count: wordCount });
    } catch (err) {
      console.error(`[rewrite] Failed for idea ${row.idea_id}:`, err);
    }
  }

  return NextResponse.json({ rewrote: results.length, results });
}
