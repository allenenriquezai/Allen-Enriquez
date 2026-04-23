import fs from "node:fs";
import path from "node:path";

export const DEFAULT_RESEARCH_PATH =
  "/Users/allenenriquez/Developer/Allen-Enriquez/projects/personal/.tmp/content-research.md";

export interface ResearchParse {
  recommendedHooks: string[];
  topHooks: string[]; // surfaced so Agent D can pick these up later for learning_refs
}

// Parse content-research.md loosely.
// - Items under "## Recommended Hooks for Allen (adapted)" → ideas.
// - Items under "## Top Hooks This Week" → surfaced for learning_refs (Agent D).
export function readResearch(
  filePath: string = DEFAULT_RESEARCH_PATH,
): ResearchParse {
  const resolved = path.resolve(filePath);
  if (!fs.existsSync(resolved)) {
    console.warn(`[research] file not found at ${resolved}`);
    return { recommendedHooks: [], topHooks: [] };
  }
  const md = fs.readFileSync(resolved, "utf8");
  return parseResearch(md);
}

export function parseResearch(md: string): ResearchParse {
  const sections = splitSections(md);
  const recommendedHooks = extractNumberedItems(
    sections["Recommended Hooks for Allen (adapted)"] ?? "",
  );
  const topHooks = extractNumberedItems(sections["Top Hooks This Week"] ?? "");
  return { recommendedHooks, topHooks };
}

// Split a markdown doc into { sectionTitle: bodyText } keyed by h2 (## ...).
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

// Pull text from "1. ..." or "- ..." style list items. Take the first line of
// each item so multi-line context notes don't bleed into the idea title.
function extractNumberedItems(body: string): string[] {
  if (!body) return [];
  const items: string[] = [];
  const lines = body.split(/\r?\n/);
  for (const line of lines) {
    const m =
      line.match(/^\s*\d+\.\s+(.+?)\s*$/) ?? line.match(/^\s*-\s+(.+?)\s*$/);
    if (m) {
      // strip surrounding quotes if present
      let text = m[1].trim();
      text = text.replace(/^["']+/, "").replace(/["']+$/, "");
      // drop trailing " — why it works" tail chunks if present on the same line
      // (keep just the hook before the first " — " separator)
      const split = text.split(/\s+—\s+/);
      text = split[0].trim();
      if (text.length > 0 && text.length < 400) items.push(text);
    }
  }
  return items;
}
