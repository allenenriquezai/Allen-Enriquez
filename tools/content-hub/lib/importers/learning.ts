import fs from "node:fs";
import path from "node:path";

export interface LearningItem {
  category: "viral_ref" | "trending_topic" | "competitor_post";
  title: string | null;
  creator: string | null;
  platform: string | null;
  notes: string | null;
  url?: string | null;
}

export interface LearningParse {
  viralRefs: LearningItem[];
  trendingTopics: LearningItem[];
  competitorPosts: LearningItem[];
}

export const DEFAULT_RESEARCH_FILES = [
  "/Users/allenenriquez/Developer/Allen-Enriquez/projects/personal/.tmp/content-research.md",
  "/Users/allenenriquez/Developer/Allen-Enriquez/projects/personal/.tmp/content-research-apr12.md",
];

// Public entrypoint — read one or many research files and merge.
export function readLearning(files: string[] = DEFAULT_RESEARCH_FILES): LearningParse {
  const merged: LearningParse = {
    viralRefs: [],
    trendingTopics: [],
    competitorPosts: [],
  };
  for (const f of files) {
    const resolved = path.resolve(f);
    if (!fs.existsSync(resolved)) {
      console.warn(`[learning] file not found at ${resolved} — skipping`);
      continue;
    }
    const md = fs.readFileSync(resolved, "utf8");
    const parsed = parseLearning(md);
    merged.viralRefs.push(...parsed.viralRefs);
    merged.trendingTopics.push(...parsed.trendingTopics);
    merged.competitorPosts.push(...parsed.competitorPosts);
  }
  return merged;
}

export function parseLearning(md: string): LearningParse {
  const sections = splitSections(md);
  const viralRefs = parseTopHooks(sections["Top Hooks This Week"] ?? "");
  const trendingTopics = parseTrendingTopics(sections["Trending Topics"] ?? "");
  const competitorPosts = parseCompetitorMoves(sections["Competitor Moves"] ?? "");
  return { viralRefs, trendingTopics, competitorPosts };
}

function splitSections(md: string): Record<string, string> {
  const out: Record<string, string> = {};
  const lines = md.split(/\r?\n/);
  let current: string | null = null;
  let buf: string[] = [];
  const flush = () => {
    if (current !== null) out[current] = buf.join("\n").trim();
  };
  for (const line of lines) {
    const m = line.match(/^##\s+(.+?)\s*$/);
    if (m) {
      flush();
      current = m[1].trim();
      buf = [];
    } else if (current !== null) {
      buf.push(line);
    }
  }
  flush();
  return out;
}

// Parse "## Top Hooks This Week" — numbered items with follow-up lines:
//   1. "Title" — @creator, platform, engagement note
//      Format: ...
//      Why it works: ...
function parseTopHooks(body: string): LearningItem[] {
  if (!body) return [];
  const items: LearningItem[] = [];
  const lines = body.split(/\r?\n/);
  let current: { header: string; follow: string[] } | null = null;
  const flush = () => {
    if (!current) return;
    const parsed = parseHookHeader(current.header);
    const notes = current.follow
      .map((l) => l.trim())
      .filter((l) => l.length > 0)
      .join(" | ");
    items.push({
      category: "viral_ref",
      title: parsed.title,
      creator: parsed.creator,
      platform: parsed.platform,
      notes: [parsed.engagement, notes].filter(Boolean).join(" | ") || null,
    });
    current = null;
  };
  for (const raw of lines) {
    const numbered = raw.match(/^\s*\d+\.\s+(.+?)\s*$/);
    if (numbered) {
      flush();
      current = { header: numbered[1].trim(), follow: [] };
    } else if (current && /^\s+\S/.test(raw)) {
      current.follow.push(raw);
    } else if (current && raw.trim() === "") {
      // blank line is part of the item until next numbered header — skip
    }
  }
  flush();
  return items;
}

function parseHookHeader(header: string): {
  title: string | null;
  creator: string | null;
  platform: string | null;
  engagement: string | null;
} {
  // Split on em-dash " — " (spaced). Title is first chunk (often quoted),
  // tail is "@creator, platform, engagement note".
  const parts = header.split(/\s+—\s+/);
  let title: string | null = null;
  let creator: string | null = null;
  let platform: string | null = null;
  let engagement: string | null = null;

  if (parts.length >= 1) {
    title = parts[0].replace(/^["']+/, "").replace(/["']+$/, "").trim() || null;
  }
  if (parts.length >= 2) {
    const tail = parts.slice(1).join(" — ");
    const csv = tail.split(",").map((s) => s.trim()).filter(Boolean);
    // Try to find the first @handle token
    const creatorIdx = csv.findIndex((c) => c.startsWith("@"));
    if (creatorIdx >= 0) {
      creator = csv[creatorIdx];
    } else if (csv.length > 0) {
      // No @handle — first chunk is the creator name (e.g. "Nate Herk")
      creator = csv[0];
    }
    // Platform: find known platform keyword in remaining chunks
    const platformRe = /\b(YouTube|TikTok|Instagram|Reels|Shorts|Facebook|FB|IG|X|Twitter)\b/i;
    for (const c of csv) {
      const m = c.match(platformRe);
      if (m) {
        platform = normalizePlatform(m[1]);
        break;
      }
    }
    // Engagement: the leftover chunks (anything that isn't creator/platform)
    const leftover = csv.filter((c) => c !== creator && !platformRe.test(c));
    engagement = leftover.join(", ") || null;
  }
  return { title, creator, platform, engagement };
}

function normalizePlatform(p: string): string {
  const low = p.toLowerCase();
  if (low === "fb") return "facebook";
  if (low === "ig") return "instagram";
  if (low === "reels") return "instagram";
  if (low === "shorts") return "youtube";
  if (low === "twitter") return "x";
  return low;
}

// Parse "## Trending Topics" — bullets like:
//   - **Topic** — description. Allen angle: "..."
function parseTrendingTopics(body: string): LearningItem[] {
  if (!body) return [];
  const items: LearningItem[] = [];
  const lines = body.split(/\r?\n/);
  for (const raw of lines) {
    const m = raw.match(/^\s*-\s+(.+?)\s*$/);
    if (!m) continue;
    const text = m[1].trim();
    const boldMatch = text.match(/^\*\*(.+?)\*\*\s*(?:—|-)?\s*(.*)$/);
    let title: string | null = null;
    let rest: string | null = null;
    if (boldMatch) {
      title = boldMatch[1].trim();
      rest = boldMatch[2].trim() || null;
    } else {
      // fallback: first sentence becomes title
      const split = text.split(/\s+—\s+/);
      title = split[0].replace(/\*\*/g, "").trim();
      rest = split.slice(1).join(" — ").trim() || null;
    }
    items.push({
      category: "trending_topic",
      title,
      creator: null,
      platform: null,
      notes: rest,
    });
  }
  return items;
}

// Parse "## Competitor Moves" — bullets like:
//   - Name: what they're doing
function parseCompetitorMoves(body: string): LearningItem[] {
  if (!body) return [];
  const items: LearningItem[] = [];
  const lines = body.split(/\r?\n/);
  for (const raw of lines) {
    const m = raw.match(/^\s*-\s+(.+?)\s*$/);
    if (!m) continue;
    const text = m[1].trim();
    // Extract name — first chunk before ":" or "—"
    let creator: string | null = null;
    let notes: string | null = text;
    const colonIdx = text.indexOf(":");
    const dashIdx = text.indexOf("—");
    let splitAt = -1;
    if (colonIdx > 0 && (dashIdx < 0 || colonIdx < dashIdx)) splitAt = colonIdx;
    else if (dashIdx > 0) splitAt = dashIdx;
    if (splitAt > 0 && splitAt < 40) {
      creator = text.slice(0, splitAt).replace(/\*\*/g, "").trim();
      notes = text.slice(splitAt + 1).trim() || null;
    }
    items.push({
      category: "competitor_post",
      title: creator,
      creator,
      platform: null,
      notes,
    });
  }
  return items;
}
