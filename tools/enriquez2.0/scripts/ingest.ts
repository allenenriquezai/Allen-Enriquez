import fs from "node:fs";
import path from "node:path";
import { SB_ROOT } from "../lib/env.js";
import { loadSources, type RawItem } from "../lib/sources.js";
import { fetchRss, fetchGithubReleases, fetchReddit } from "../lib/fetchers.js";
import { routeItem } from "../lib/router.js";
import type { Domain } from "../lib/identity.js";

const DOMAINS: Domain[] = ["build", "reach", "serve"];

function parseSince(s: string): number {
  const m = s.match(/^(\d+)([dhm])$/);
  if (!m) throw new Error(`bad --since: ${s}`);
  const n = parseInt(m[1], 10);
  const mult = m[2] === "d" ? 86400_000 : m[2] === "h" ? 3600_000 : 60_000;
  return Date.now() - n * mult;
}

function parseArgs() {
  const args = process.argv.slice(2);
  let domain: Domain | "all" = "all";
  let sinceMs = Date.now() - 7 * 86400_000;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--domain") domain = args[++i] as Domain | "all";
    else if (args[i] === "--since") sinceMs = parseSince(args[++i]);
  }
  return { domain, sinceMs };
}

async function fetchForDomain(domain: Domain, sinceMs: number): Promise<RawItem[]> {
  const cfg = loadSources(domain);
  const out: RawItem[] = [];
  if (cfg.rss) {
    for (const url of cfg.rss) out.push(...(await fetchRss(url, sinceMs)));
  }
  if (cfg.github_releases) {
    for (const repo of cfg.github_releases) out.push(...(await fetchGithubReleases(repo, sinceMs)));
  }
  if (cfg.reddit?.subreddits) {
    const thr = cfg.reddit.hot_threshold ?? 100;
    for (const sub of cfg.reddit.subreddits) out.push(...(await fetchReddit(sub, sinceMs, thr)));
  }
  return out;
}

function dedupeById(items: RawItem[]): RawItem[] {
  const seen = new Set<string>();
  const out: RawItem[] = [];
  for (const it of items) {
    if (seen.has(it.id)) continue;
    seen.add(it.id);
    out.push(it);
  }
  return out;
}

function writeRaw(domainHint: string, items: RawItem[]) {
  if (items.length === 0) return;
  const dir = path.join(SB_ROOT, "raw", domainHint);
  fs.mkdirSync(dir, { recursive: true });
  const today = new Date().toISOString().slice(0, 10);
  const file = path.join(dir, `${today}.jsonl`);
  fs.appendFileSync(file, items.map((it) => JSON.stringify(it)).join("\n") + "\n");
}

interface InboxRow {
  date: string;
  title: string;
  source: string;
  why: string;
  url: string;
  relevance: number;
  topic: string;
}

interface TopicRecord {
  count: number;
  domain: Domain;
  first_seen: string;
  last_seen: string;
}

function migrateInboxHeader(content: string): string {
  // If existing inbox lacks Topic column, add it.
  const lines = content.split("\n");
  let headerIdx = lines.findIndex((l) => /^\|\s*Date\s*\|/i.test(l));
  if (headerIdx < 0) return content;
  if (lines[headerIdx].toLowerCase().includes("topic")) return content;
  lines[headerIdx] = lines[headerIdx].replace(/\|\s*Why\s*\|/i, "| Why | Topic |");
  // Update the separator row that follows
  if (lines[headerIdx + 1] && /^\|---/.test(lines[headerIdx + 1])) {
    const sep = lines[headerIdx + 1];
    const cellCount = (sep.match(/\|/g) ?? []).length - 1;
    const targetCount = cellCount + 1;
    lines[headerIdx + 1] = "|" + "---|".repeat(targetCount);
  }
  return lines.join("\n");
}

function appendInbox(targetDomain: Domain, rows: InboxRow[]) {
  if (rows.length === 0) return;
  const file = path.join(SB_ROOT, "domains", targetDomain, "inbox.md");
  let content = fs.readFileSync(file, "utf8");
  content = migrateInboxHeader(content);
  const existingUrls = new Set<string>();
  for (const m of content.matchAll(/\(([^)]+)\)/g)) existingUrls.add(m[1]);
  const newRows = rows.filter((r) => !existingUrls.has(r.url));
  if (newRows.length === 0) return;
  newRows.sort((a, b) => b.relevance - a.relevance);
  const lines = newRows.map(
    (r) =>
      `| ${r.date} | ${esc(r.title)} | ${esc(r.source)} | ${esc(r.why)} (rel ${r.relevance}) | \`${esc(r.topic)}\` | [link](${r.url}) | new |`,
  );
  content = content.trimEnd() + "\n" + lines.join("\n") + "\n";
  fs.writeFileSync(file, content);
  console.log(`[inbox:${targetDomain}] +${newRows.length}`);
}

function updateTopicsRegistry(rows: InboxRow[], domain: Domain) {
  const file = path.join(SB_ROOT, "topics.json");
  let registry: Record<string, TopicRecord> = {};
  if (fs.existsSync(file)) {
    try {
      registry = JSON.parse(fs.readFileSync(file, "utf8")) as Record<string, TopicRecord>;
    } catch {
      registry = {};
    }
  }
  const today = new Date().toISOString().slice(0, 10);
  for (const r of rows) {
    if (!r.topic || r.topic === "drop" || r.topic === "uncategorized") continue;
    const key = `${domain}/${r.topic}`;
    const existing = registry[key];
    if (existing) {
      existing.count++;
      existing.last_seen = today;
    } else {
      registry[key] = { count: 1, domain, first_seen: today, last_seen: today };
    }
  }
  fs.writeFileSync(file, JSON.stringify(registry, null, 2));
}

function esc(s: string): string {
  return s.replace(/\|/g, "\\|").replace(/\n/g, " ").trim();
}

async function main() {
  const { domain, sinceMs } = parseArgs();
  const targets: Domain[] = domain === "all" ? DOMAINS : [domain];
  const inboxByDomain: Record<Domain, InboxRow[]> = { build: [], reach: [], serve: [] };

  for (const sourceDomain of targets) {
    console.log(`[fetch:${sourceDomain}] starting`);
    const raw = dedupeById(await fetchForDomain(sourceDomain, sinceMs));
    writeRaw(sourceDomain, raw);
    console.log(`[fetch:${sourceDomain}] ${raw.length} raw items`);

    let routed = 0;
    let kept = 0;
    for (const it of raw) {
      const r = await routeItem(it);
      routed++;
      if (r.tag === "drop" || r.relevance < 6) continue;
      const tag = r.tag as Domain;
      kept++;
      inboxByDomain[tag].push({
        date: it.published_at.slice(0, 10),
        title: it.title,
        source: it.source,
        why: r.why,
        url: it.url,
        relevance: r.relevance,
        topic: r.topic,
      });
    }
    console.log(`[route:${sourceDomain}] ${routed} routed, ${kept} kept`);
  }

  for (const d of DOMAINS) {
    appendInbox(d, inboxByDomain[d]);
    updateTopicsRegistry(inboxByDomain[d], d);
  }
  console.log("[done]");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
