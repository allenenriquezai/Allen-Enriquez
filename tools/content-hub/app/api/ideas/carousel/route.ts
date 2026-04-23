import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You write carousel post copy for Allen, an AI automation consultant, adapting his short-form video scripts into slide-by-slide carousel format.

Carousel structure (5–7 slides):
SLIDE 1 (Cover): Bold hook — same energy as the reel opening. Max 8 words.
SLIDE 2–5: One key point per slide. Each slide: 1 headline (max 6 words) + 1–2 sentences of detail.
FINAL SLIDE (CTA): One clear action. "Drop [WORD] in the comments" or "Follow for more".

Brand voice: direct, honest, proof-first. Real numbers and examples where possible. No hype.

Format your output exactly like this:
SLIDE 1: [text]
SLIDE 2: [text]
SLIDE 3: [text]
...
SLIDE N: [text]

Return ONLY the slide content, no preamble.`;

export async function POST(req: Request) {
  let body: { idea_id?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const ideaId = body.idea_id;
  if (!ideaId || !Number.isFinite(ideaId)) {
    return NextResponse.json({ error: "idea_id required" }, { status: 400 });
  }

  const idea = db
    .prepare("SELECT title, hook FROM ideas WHERE id = ?")
    .get(ideaId) as { title: string; hook: string | null } | undefined;

  if (!idea) return NextResponse.json({ error: "idea not found" }, { status: 404 });

  const reelScript = db
    .prepare("SELECT body FROM scripts WHERE idea_id = ? AND variant = 'reel'")
    .get(ideaId) as { body: string } | undefined;

  const userPrompt = `Title: ${idea.title}
Hook: ${idea.hook ?? "(none)"}
Reel script:
${reelScript?.body?.trim() || "(no reel script yet — create carousel based on title and hook)"}

Write the carousel slides now.`;

  let carouselBody: string;

  try {
    const msg = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userPrompt }],
    });
    carouselBody = msg.content[0].type === "text" ? msg.content[0].text.trim() : "";
  } catch (err) {
    console.error("[carousel] Claude error:", err);
    return NextResponse.json({ error: "Generation failed" }, { status: 500 });
  }

  const wordCount = carouselBody.split(/\s+/).filter(Boolean).length;

  const existing = db
    .prepare("SELECT id FROM scripts WHERE idea_id = ? AND variant = 'carousel'")
    .get(ideaId) as { id: number } | undefined;

  if (existing) {
    db.prepare("UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
      .run(carouselBody, wordCount, existing.id);
  } else {
    db.prepare("INSERT INTO scripts (idea_id, variant, body, word_count) VALUES (?, 'carousel', ?, ?)")
      .run(ideaId, carouselBody, wordCount);
  }

  return NextResponse.json({ ok: true, idea_id: ideaId, body: carouselBody, word_count: wordCount });
}
