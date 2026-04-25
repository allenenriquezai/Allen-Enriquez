import Anthropic from "@anthropic-ai/sdk";
import { loadIdentity, DOMAIN_DEFINITIONS, type Domain } from "./identity.js";
import type { RawItem } from "./sources.js";
import { requireEnv } from "./env.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

export interface RoutedItem {
  tag: Domain | "drop";
  relevance: number;
  why: string;
  topic: string;
}

const SYSTEM = `You route world-knowledge items into Allen's Enriquez2.0 engine.

You will receive: (1) Allen's identity (who he is, becoming, Q2 theme, values), (2) the three domain definitions, (3) one item (title + content + source).

Decide:
- tag: which domain this item fits ("build" | "reach" | "serve" | "drop")
- relevance: 0-10 — how directly this serves Allen's Q2 theme (first paid client by June, 10k followers as engine)
- why: 1 short sentence — concrete reason it's relevant or being dropped
- topic: a short kebab-case tag identifying the SPECIFIC sub-area within the domain (e.g. "claude-code", "mcp-tools", "folder-structure", "agent-design", "prompt-caching", "linkedin-cadence", "viral-hooks", "short-form-format", "creator-monetization", "cold-outreach", "lead-magnets", "consultancy-pricing", "client-onboarding", "saas-positioning"). Topics are emergent — invent specific ones, don't pad to a fixed list. Lowercase, 1-3 words, hyphenated.

Drop rules: drop if generic news, pure entertainment, off-domain (politics/sports), already-known-basic, or relevance < 5.

Domains:
- build: ${DOMAIN_DEFINITIONS.build}
- reach: ${DOMAIN_DEFINITIONS.reach}
- serve: ${DOMAIN_DEFINITIONS.serve}

Output ONLY valid JSON: {"tag":"build|reach|serve|drop","relevance":0-10,"why":"...","topic":"kebab-case"} — no prose, no markdown fences. For drops, set topic to "drop".`;

export async function routeItem(item: RawItem): Promise<RoutedItem> {
  const identity = loadIdentity();
  const userMsg = `IDENTITY:\n${identity}\n\nITEM:\nsource: ${item.source}\ntitle: ${item.title}\ncontent: ${item.content.slice(0, 1500)}\nurl: ${item.url}`;

  const res = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 200,
    system: SYSTEM,
    messages: [{ role: "user", content: userMsg }],
  });
  const text = res.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) {
    return { tag: "drop", relevance: 0, why: `parse fail: ${text.slice(0, 80)}`, topic: "drop" };
  }
  try {
    const parsed = JSON.parse(m[0]) as RoutedItem;
    if (!parsed.topic) parsed.topic = "uncategorized";
    return parsed;
  } catch {
    return { tag: "drop", relevance: 0, why: "json parse error", topic: "drop" };
  }
}
