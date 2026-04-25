import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You generate short-form video script ideas for Allen, an AI automation consultant.

Allen's profile:
- Runs sales for EPS Painting & Cleaning in Brisbane, AU (manages team remotely from Philippines)
- Generates $60–100K/month in new revenue using AI automation (n8n, Claude Code)
- Audience: small business owners, VAs, semi-technical professionals
- Tone: direct, honest, proof-first — real results, not hype

Content pillars:
- fundamental: "What is X?" explainers (Claude, AI agents, n8n, automation)
- before_after_proof: Before/after stories showing revenue or time saved
- behind_scenes: How Allen built a specific automation or system
- quick_tip: One actionable steal-worthy tip
- contrarian: Pushback on common AI advice

Hook formulas to rotate through (from Justyn.ai / Sabrina Ramonov):
- Cheat-code: "Here's the cheat code for [problem]"
- Tool-swap: "I replaced [old way] with [AI tool] — here's what happened"
- Steal-my-system: "Steal my exact [system] for [outcome]"
- Social-proof-opener: "I went from [bad] to [good] using [thing]"
- Question hook: "What would you do if [scenario]?"

Reel script structure (80–120 words, ~60–90 sec):
- Hook (1 sentence)
- Explain (1–2 sentences)
- Illustrate (1–2 sentences, specific real example)
- Takeaway (1 sentence)
No buzzwords ("game-changer", "revolutionary", "unlock"). Direct, concrete.

Output: A JSON array of exactly the requested count of ideas. Each object:
{
  "title": "Short punchy title (max 8 words)",
  "hook": "Opening line (1–2 sentences, grabs attention)",
  "pillar": one of: fundamental | before_after_proof | behind_scenes | quick_tip | contrarian,
  "modeled_after": one of: justyn.ai | sabrina_ramonov | dan_martell | greg_isenberg | original,
  "reel_script": "Full 80–120 word reel script body (Hook→Explain→Illustrate→Takeaway). Plain text, no headers."
}

Rules:
- Vary pillars across the batch (unless a theme is specified)
- No duplicate topics from the existing titles list
- Be specific — real tool names, real numbers where plausible
- Return ONLY valid JSON, no commentary`;

export async function POST(req: Request) {
  let body: { count?: number; day_of_week?: string; theme?: string; pillar?: string; batch?: string };
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const count = Math.min(Math.max(1, body.count ?? 10), 20);
  const dayOfWeek = body.day_of_week ?? null;
  const theme = body.theme ?? null;
  const pillarHint = body.pillar ?? null;
  const batch = body.batch ?? "ai_generated";

  const existingRows = db
    .prepare("SELECT title FROM ideas ORDER BY id DESC LIMIT 100")
    .all() as { title: string }[];
  const existingTitles = existingRows.map((r) => r.title);

  const dayContext = dayOfWeek
    ? `\n\nTarget day of week: ${dayOfWeek}. Weight ideas toward content that fits posting on that day.`
    : "";
  const themeContext = theme
    ? `\n\nTheme for this batch: "${theme}". Every idea should fit this format/angle.${pillarHint ? ` Lean toward the "${pillarHint}" pillar.` : ""}`
    : "";

  const userPrompt = `Generate ${count} fresh script ideas. Each idea must include a complete reel_script.

Existing titles to avoid repeating (themes or topics):
${existingTitles.slice(0, 50).map((t) => `- ${t}`).join("\n")}${dayContext}${themeContext}

Return a JSON array of ${count} objects.`;

  let ideas: Array<{
    title: string;
    hook: string;
    pillar: string;
    modeled_after: string;
    reel_script?: string;
  }>;

  try {
    const msg = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 8192,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userPrompt }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "";
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (!jsonMatch) throw new Error("No JSON array in response");
    ideas = JSON.parse(jsonMatch[0]);
  } catch (err) {
    console.error("[generate] Claude error:", err);
    return NextResponse.json({ error: "Generation failed" }, { status: 500 });
  }

  const inserted: Array<{ id: number }> = [];

  const insertIdea = db.prepare(
    `INSERT INTO ideas (title, hook, pillar, modeled_after, status, batch, day_of_week, theme)
     VALUES (?, ?, ?, ?, 'new', ?, ?, ?)`,
  );
  const insertScript = db.prepare(
    `INSERT INTO scripts (idea_id, variant, body, word_count) VALUES (?, 'reel', ?, ?)`,
  );

  for (const idea of ideas) {
    if (!idea.title) continue;
    const info = insertIdea.run(
      idea.title,
      idea.hook ?? null,
      idea.pillar ?? "fundamental",
      idea.modeled_after ?? null,
      batch,
      dayOfWeek,
      theme,
    );
    const ideaId = Number(info.lastInsertRowid);
    if (idea.reel_script && idea.reel_script.trim()) {
      const wordCount = idea.reel_script.split(/\s+/).filter(Boolean).length;
      insertScript.run(ideaId, idea.reel_script.trim(), wordCount);
    }
    inserted.push({ id: ideaId });
  }

  if (inserted.length === 0) {
    return NextResponse.json({ ideas: [], count: 0 });
  }

  const rows = db
    .prepare(
      `SELECT i.id AS idea_id, i.title, i.hook, i.pillar, i.modeled_after, i.status, i.notes,
              s.id AS script_id, s.body AS reel_body
       FROM ideas i
       LEFT JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
       WHERE i.id IN (${inserted.map(() => "?").join(",")})
       ORDER BY i.id DESC`,
    )
    .all(...inserted.map((r) => r.id)) as Array<{
    idea_id: number;
    title: string;
    hook: string | null;
    pillar: string | null;
    modeled_after: string | null;
    status: string;
    notes: string | null;
    script_id: number | null;
    reel_body: string | null;
  }>;

  const result = rows.map((r) => ({
    ideaId: r.idea_id,
    title: r.title,
    hook: r.hook,
    pillar: r.pillar,
    modeledAfter: r.modeled_after,
    status: r.status,
    notes: r.notes,
    scriptId: r.script_id,
    reelBody: r.reel_body,
    hasCarousel: false,
  }));

  return NextResponse.json({ ideas: result, count: result.length });
}
