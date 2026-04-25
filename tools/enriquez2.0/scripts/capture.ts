import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { SB_ROOT, requireEnv } from "../lib/env.js";
import { routeItem } from "../lib/router.js";
import type { RawItem } from "../lib/sources.js";
import type { Domain } from "../lib/identity.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

function parseArgs(): string {
  const args = process.argv.slice(2);
  const url = args.find((a) => /^https?:\/\//.test(a));
  if (!url) throw new Error("usage: npm run capture -- <url>");
  return url;
}

function hash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return Math.abs(h).toString(36);
}

async function fetchPage(url: string): Promise<{ title: string; text: string }> {
  const res = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 enriquez2.0/0.1",
    },
  });
  if (!res.ok) throw new Error(`fetch ${url}: ${res.status}`);
  const html = await res.text();
  const title = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? url).replace(/\s+/g, " ").trim();
  // Strip script/style blocks
  const stripped = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return { title, text: stripped.slice(0, 12000) };
}

const SUMMARY_SYSTEM = `You summarize a captured URL into a clean, useful inbox row for Allen's Enriquez2.0 engine.

Input: title + raw page text (cleaned of HTML).
Output JSON: {"clean_title": "...", "summary": "..."}.

Rules:
- clean_title: 5-12 words, drop "| Site Name" suffixes and clickbait fluff.
- summary: 2-4 sentences. What is this? What's the actionable insight? No fluff. No "the article discusses".
- Output JSON only, no markdown fences.`;

async function summarize(title: string, text: string): Promise<{ clean_title: string; summary: string }> {
  const res = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 500,
    system: SUMMARY_SYSTEM,
    messages: [{ role: "user", content: `TITLE: ${title}\n\nTEXT:\n${text}` }],
  });
  const out = res.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");
  const m = out.match(/\{[\s\S]*\}/);
  if (!m) return { clean_title: title, summary: text.slice(0, 400) };
  try {
    return JSON.parse(m[0]);
  } catch {
    return { clean_title: title, summary: text.slice(0, 400) };
  }
}

function appendInbox(domain: Domain, row: { title: string; source: string; why: string; url: string; relevance: number; topic: string }) {
  const file = path.join(SB_ROOT, "domains", domain, "inbox.md");
  let content = fs.readFileSync(file, "utf8");
  if (content.includes(`(${row.url})`)) {
    console.log(`[capture] already in ${domain} inbox — skipping`);
    return;
  }
  const date = new Date().toISOString().slice(0, 10);
  const esc = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ").trim();
  const line = `| ${date} | ${esc(row.title)} | ${esc(row.source)} | ${esc(row.why)} (rel ${row.relevance}) | \`${esc(row.topic)}\` | [link](${row.url}) | new |`;
  content = content.trimEnd() + "\n" + line + "\n";
  fs.writeFileSync(file, content);
  console.log(`[capture] +1 to ${domain}/inbox.md (topic: ${row.topic}, rel ${row.relevance})`);
}

function updateTopicsRegistry(domain: Domain, topic: string) {
  if (!topic || topic === "drop" || topic === "uncategorized") return;
  const file = path.join(SB_ROOT, "topics.json");
  let registry: Record<string, { count: number; domain: Domain; first_seen: string; last_seen: string }> = {};
  if (fs.existsSync(file)) {
    try {
      registry = JSON.parse(fs.readFileSync(file, "utf8"));
    } catch {
      registry = {};
    }
  }
  const key = `${domain}/${topic}`;
  const today = new Date().toISOString().slice(0, 10);
  if (registry[key]) {
    registry[key].count++;
    registry[key].last_seen = today;
  } else {
    registry[key] = { count: 1, domain, first_seen: today, last_seen: today };
  }
  fs.writeFileSync(file, JSON.stringify(registry, null, 2));
}

async function main() {
  const url = parseArgs();
  console.log(`[capture] fetching ${url}`);
  const { title, text } = await fetchPage(url);

  console.log(`[capture] summarizing via Haiku...`);
  const { clean_title, summary } = await summarize(title, text);

  const item: RawItem = {
    id: `capture:${hash(url)}`,
    source: `capture:${new URL(url).hostname}`,
    title: clean_title,
    url,
    content: summary,
    published_at: new Date().toISOString(),
  };

  console.log(`[capture] routing via Haiku...`);
  const r = await routeItem(item);
  if (r.tag === "drop") {
    console.log(`[capture] DROPPED — ${r.why}`);
    return;
  }
  console.log(`[capture] tag=${r.tag} relevance=${r.relevance} topic=${r.topic}`);
  console.log(`[capture] why: ${r.why}`);

  appendInbox(r.tag as Domain, {
    title: clean_title,
    source: item.source,
    why: r.why,
    url,
    relevance: r.relevance,
    topic: r.topic,
  });
  updateTopicsRegistry(r.tag as Domain, r.topic);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
