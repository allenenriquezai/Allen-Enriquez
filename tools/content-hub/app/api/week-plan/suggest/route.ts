import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import db from "@/lib/db";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const SYSTEM_PROMPT = `You plan a content week for Allen, an AI automation consultant building his personal brand.

Allen's 5 content pillars:
- fundamental: explainers ("What is Claude / n8n / agents?")
- before_after_proof: revenue or time-saved stories from real client work
- behind_scenes: how a specific automation was built
- quick_tip: one steal-worthy actionable
- contrarian: pushback on common AI advice

Goal: a balanced week that mixes pillars and themes. Don't post the same theme two days in a row. Don't repeat last week's themes.

Output: JSON array of exactly 7 objects, one per day, in Mon→Sun order.
Each object:
{
  "day": "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun",
  "theme": "Short label (2–4 words). e.g. 'Tutorial', 'Before/After Win', 'Hot Take', 'Build-In-Public'",
  "pillar": one of: fundamental | before_after_proof | behind_scenes | quick_tip | contrarian,
  "rationale": "One sentence on why this theme this day"
}

Return ONLY the JSON array.`;

export async function POST(req: Request) {
  let body: { week_start?: string };
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const weekStart = body.week_start ?? new Date().toISOString().slice(0, 10);

  // Pull last 14 days of posted/scheduled themes for de-dup context
  const recent = db
    .prepare(
      `SELECT DISTINCT i.theme, i.pillar
       FROM ideas i
       WHERE i.theme IS NOT NULL
         AND i.created_at >= datetime('now', '-14 days')
       LIMIT 20`,
    )
    .all() as { theme: string; pillar: string | null }[];

  const recentContext = recent.length
    ? `\n\nRecent themes (last 14 days, avoid repeating):\n${recent.map((r) => `- ${r.theme} (${r.pillar ?? "?"})`).join("\n")}`
    : "";

  const userPrompt = `Plan the content week starting Monday ${weekStart}.${recentContext}

Return 7 day-themes Mon→Sun.`;

  try {
    const msg = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1500,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userPrompt }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "";
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (!jsonMatch) throw new Error("No JSON array");
    const proposals = JSON.parse(jsonMatch[0]) as Array<{
      day: string;
      theme: string;
      pillar: string;
      rationale: string;
    }>;

    // Normalize to Mon→Sun order
    const ordered = DAYS.map((d) => {
      const found = proposals.find((p) => p.day === d);
      return (
        found ?? {
          day: d,
          theme: "Open slot",
          pillar: "fundamental",
          rationale: "Auto-filled placeholder.",
        }
      );
    });

    return NextResponse.json({ week_start: weekStart, themes: ordered });
  } catch (err) {
    console.error("[week-plan/suggest] error:", err);
    return NextResponse.json({ error: "Suggest failed" }, { status: 500 });
  }
}
