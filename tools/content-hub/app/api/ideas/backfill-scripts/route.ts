import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You write short-form video scripts for Allen, an AI automation consultant.

Brand voice: direct, honest, proof-first. Not hype. Real results from real work.
Audience: small business owners, VAs, semi-technical professionals.

Script structure:
- Hook (1 sentence)
- Explain (1–2 sentences, what and why)
- Illustrate (1–2 sentences, specific real example)
- Takeaway (1 sentence)

Constraints:
- 80–120 words total (60–90 second reel)
- No buzzwords ("game-changer", "revolutionary", "unlock your potential")
- Plain text, no headers, no markdown

Return ONLY the script body.`;

type IdeaRow = {
  idea_id: number;
  title: string;
  hook: string | null;
  pillar: string | null;
  notes: string | null;
};

export async function POST(req: Request) {
  let body: { limit?: number; idea_ids?: number[] };
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const limit = Math.min(Math.max(1, body.limit ?? 50), 100);
  const targetIds = Array.isArray(body.idea_ids) && body.idea_ids.length > 0 ? body.idea_ids : null;

  let rows: IdeaRow[];
  if (targetIds) {
    const placeholders = targetIds.map(() => "?").join(",");
    rows = db
      .prepare(
        `SELECT i.id AS idea_id, i.title, i.hook, i.pillar, i.notes
         FROM ideas i
         LEFT JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
         WHERE i.id IN (${placeholders}) AND s.id IS NULL`,
      )
      .all(...targetIds) as IdeaRow[];
  } else {
    rows = db
      .prepare(
        `SELECT i.id AS idea_id, i.title, i.hook, i.pillar, i.notes
         FROM ideas i
         LEFT JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
         WHERE s.id IS NULL AND i.status NOT IN ('dismissed')
         ORDER BY i.id DESC
         LIMIT ?`,
      )
      .all(limit) as IdeaRow[];
  }

  if (rows.length === 0) {
    return NextResponse.json({ generated: 0, results: [] });
  }

  const insertScript = db.prepare(
    `INSERT INTO scripts (idea_id, variant, body, word_count) VALUES (?, 'reel', ?, ?)`,
  );

  const results: Array<{ id: number; title: string; body: string }> = [];

  for (const row of rows) {
    const userPrompt = `Title: ${row.title}
Hook: ${row.hook ?? "(none)"}
Pillar: ${row.pillar ?? "fundamental"}
Notes: ${row.notes?.trim() || "(none)"}

Write the reel script.`;

    try {
      const msg = await client.messages.create({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 512,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userPrompt }],
      });

      const newBody = msg.content[0].type === "text" ? msg.content[0].text.trim() : "";
      if (!newBody) continue;
      const wordCount = newBody.split(/\s+/).filter(Boolean).length;
      insertScript.run(row.idea_id, newBody, wordCount);
      results.push({ id: row.idea_id, title: row.title, body: newBody });
    } catch (err) {
      console.error(`[backfill-scripts] failed idea ${row.idea_id}:`, err);
    }
  }

  return NextResponse.json({ generated: results.length, results });
}
