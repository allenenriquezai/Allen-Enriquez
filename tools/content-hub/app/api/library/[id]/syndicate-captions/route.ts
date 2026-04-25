import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";
import { countWords } from "@/lib/importers/drafts";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const PLATFORM_SPECS = {
  caption_fb: {
    label: "Facebook",
    limit: 63206,
    style: "conversational, longer-form OK, can include context",
  },
  caption_ig: {
    label: "Instagram",
    limit: 2200,
    style: "hook-first, line breaks for scannability, 3-5 hashtags max",
  },
  caption_yt: {
    label: "YouTube",
    limit: 5000,
    style: "title-style first line then description, SEO-friendly",
  },
  caption_tiktok: {
    label: "TikTok",
    limit: 2200,
    style: "punchy hook, casual, 2-3 hashtags",
  },
  caption_x: {
    label: "X",
    limit: 280,
    style: "single thought, no hashtags unless critical",
  },
  caption_linkedin: {
    label: "LinkedIn",
    limit: 3000,
    style: "business framing, lessons/insights, no emoji abuse",
  },
} as const;

type Variant = keyof typeof PLATFORM_SPECS;

const SYSTEM = `You rewrite Allen's content captions across platforms.
Brand voice: direct, honest, proof-first. Real results from real work. No hype, no buzzwords.
Audience: small business owners, VAs, semi-technical professionals.
Preserve the core message + facts. Only change framing, length, and tone for each platform.
Return ONLY valid JSON matching the requested schema. No preamble, no code fences.`;

export async function POST(req: Request) {
  let payload: { sourceVariant?: string; sourceBody?: string; ideaId?: number };
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const { sourceVariant, sourceBody, ideaId } = payload;
  if (!sourceBody?.trim() || !ideaId || !sourceVariant) {
    return NextResponse.json(
      { error: "sourceVariant, sourceBody, ideaId required" },
      { status: 400 },
    );
  }
  if (!(sourceVariant in PLATFORM_SPECS)) {
    return NextResponse.json({ error: "unknown sourceVariant" }, { status: 400 });
  }

  const targets = (Object.keys(PLATFORM_SPECS) as Variant[]).filter(
    (k) => k !== sourceVariant,
  );

  const targetSpec = targets
    .map(
      (k) =>
        `- ${k} (${PLATFORM_SPECS[k].label}, max ${PLATFORM_SPECS[k].limit} chars): ${PLATFORM_SPECS[k].style}`,
    )
    .join("\n");

  const userPrompt = `Source platform: ${sourceVariant} (${PLATFORM_SPECS[sourceVariant as Variant].label})
Source caption:
${sourceBody.trim()}

Rewrite for these platforms:
${targetSpec}

Return JSON object: { ${targets.map((k) => `"${k}": "..."`).join(", ")} }`;

  let parsed: Record<string, string>;
  try {
    const msg = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 4096,
      system: SYSTEM,
      messages: [{ role: "user", content: userPrompt }],
    });
    const text = msg.content[0].type === "text" ? msg.content[0].text : "";
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ error: "no json in response" }, { status: 502 });
    }
    parsed = JSON.parse(jsonMatch[0]);
  } catch (err) {
    console.error("[syndicate-captions] Claude call failed:", err);
    return NextResponse.json({ error: "claude call failed" }, { status: 502 });
  }

  const findExisting = db.prepare(
    `SELECT id FROM scripts WHERE idea_id = ? AND variant = ?`,
  );
  const updateRow = db.prepare(
    `UPDATE scripts SET body = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
  );
  const insertRow = db.prepare(
    `INSERT INTO scripts (idea_id, variant, body, word_count, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
  );

  const results: Record<string, string> = {};
  for (const variant of targets) {
    let body = (parsed[variant] ?? "").trim();
    if (!body) continue;
    const limit = PLATFORM_SPECS[variant].limit;
    if (body.length > limit) body = body.slice(0, limit);
    const wc = countWords(body);
    const existing = findExisting.get(ideaId, variant) as { id: number } | undefined;
    if (existing) updateRow.run(body, wc, existing.id);
    else insertRow.run(ideaId, variant, body, wc);
    results[variant] = body;
  }

  return NextResponse.json({ captions: results });
}
