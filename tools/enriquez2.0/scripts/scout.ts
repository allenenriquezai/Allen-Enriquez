import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { SB_ROOT, requireEnv } from "../lib/env.js";
import { loadIdentity, type Domain } from "../lib/identity.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

const DOMAINS: Domain[] = ["build", "reach", "serve"];

interface TopicRecord {
  count: number;
  domain: Domain;
  first_seen: string;
  last_seen: string;
}

function loadTopics(): Record<string, TopicRecord> {
  const file = path.join(SB_ROOT, "topics.json");
  if (!fs.existsSync(file)) return {};
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

function summarizeTopics(topics: Record<string, TopicRecord>): string {
  const byDomain: Record<Domain, Array<[string, TopicRecord]>> = { build: [], reach: [], serve: [] };
  for (const [key, rec] of Object.entries(topics)) {
    byDomain[rec.domain].push([key.split("/").slice(1).join("/"), rec]);
  }
  const out: string[] = [];
  for (const d of DOMAINS) {
    out.push(`=== ${d.toUpperCase()} (${byDomain[d].length} topics tracked) ===`);
    if (byDomain[d].length === 0) {
      out.push("(none yet)");
    } else {
      byDomain[d].sort((a, b) => b[1].count - a[1].count);
      for (const [topic, rec] of byDomain[d].slice(0, 30)) {
        out.push(`- ${topic} — count ${rec.count}, last ${rec.last_seen}`);
      }
    }
  }
  return out.join("\n");
}

function loadDomainStandards(): string {
  const out: string[] = [];
  for (const d of DOMAINS) {
    const p = path.join(SB_ROOT, "domains", d, "standard.md");
    if (fs.existsSync(p)) {
      const txt = fs.readFileSync(p, "utf8").slice(0, 4000);
      out.push(`=== ${d.toUpperCase()} standard ===\n${txt}`);
    }
  }
  return out.join("\n\n");
}

const SYSTEM = `You are Allen's scout. Your job: find BLIND SPOTS — topics he should be tracking but isn't yet.

You receive: (1) Allen's identity (Q2 anchor: first paid client by June 2026, 10k followers as engine), (2) the current topics he IS tracking per domain, (3) the current per-domain standards.

For each domain (BUILD / REACH / SERVE), name 2-4 topics he is NOT tracking that he SHOULD be — given:
- where the AI / creator / consultancy industry is heading right now (April 2026)
- topics that are obviously load-bearing for his Q2 anchor
- gaps between what world-class operators care about and what he's seeing in his inbox

For each blind spot:
- topic_slug: kebab-case
- why_it_matters: 1-2 sentences tying to Q2 anchor
- where_to_source: 1-2 concrete sources (RSS feed URL, subreddit, newsletter name, creator handle, GitHub repo) Allen could add to sources.yaml
- urgency: 1-5 (5 = he's losing ground every day this isn't tracked)

Drop:
- Generic advice ("track viral content")
- Topics he is already tracking (cross-check the registry)
- Trendy nonsense without Q2 leverage

Output strict markdown, no preamble:

# Blind Spots — {YYYY-MM-DD}

## BUILD
1. **{topic-slug}** — {why_it_matters}
   Source: {where_to_source}
   Urgency: {1-5}

(repeat 2-4 per domain)

## REACH
...

## SERVE
...

## Sources to add (one-shot)
- {domain}: {source — paste-ready for sources.yaml}

Rules:
- Be specific. "agent-evals" not "AI quality". "linkedin-newsletter-cadence" not "LinkedIn".
- Cite real RSS URLs / subreddit names / creator handles when possible. If unsure, label "(verify)".
- Quality over quantity. 2 sharp gaps > 4 vague ones.`;

async function main() {
  const today = new Date().toISOString().slice(0, 10);
  const identity = loadIdentity();
  const topics = loadTopics();
  const standards = loadDomainStandards();

  const totalTopics = Object.keys(topics).length;
  console.log(`[scout] ${totalTopics} topics tracked. calling Sonnet...`);

  const userMsg = `IDENTITY:\n${identity}\n\nTOPICS CURRENTLY TRACKED:\n${summarizeTopics(topics)}\n\nCURRENT STANDARDS:\n${standards}\n\nToday's date: ${today}`;

  const res = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4000,
    system: SYSTEM,
    messages: [{ role: "user", content: userMsg }],
  });
  const text = res.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");

  const dir = path.join(SB_ROOT, "scout");
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, `${today}.md`);
  fs.writeFileSync(out, text);
  console.log(`[scout] wrote scout/${today}.md (${text.length} chars)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
