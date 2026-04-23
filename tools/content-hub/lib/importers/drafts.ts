import fs from "node:fs";
import path from "node:path";

export interface DraftRow {
  day: string;
  slot: number;
  type: string;
  title: string;
  lane?: string;
  category?: string;
  modeled_after?: string;
  platforms?: string[];
  script: string;
  word_count?: number;
  status?: string;
  generated?: string;
  batch?: string;
}

// Default location — Allen's .tmp dir outside this repo.
export const DEFAULT_DRAFTS_PATH =
  "/Users/allenenriquez/Developer/Allen-Enriquez/.tmp/content_drafts.json";

export function readDrafts(filePath: string = DEFAULT_DRAFTS_PATH): DraftRow[] {
  const resolved = path.resolve(filePath);
  if (!fs.existsSync(resolved)) {
    console.warn(`[drafts] file not found at ${resolved} — returning []`);
    return [];
  }
  const raw = fs.readFileSync(resolved, "utf8");
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      console.warn("[drafts] expected array at root — got", typeof parsed);
      return [];
    }
    return parsed as DraftRow[];
  } catch (err) {
    console.error("[drafts] JSON parse error:", err);
    return [];
  }
}

// Maps a draft "type" (reel | youtube | carousel | caption_* | ...) to the
// scripts.variant vocabulary used by the schema.
export function mapTypeToVariant(type: string): string {
  const t = (type || "").toLowerCase().trim();
  if (t === "reel" || t === "short" || t === "shorts") return "reel";
  if (t === "youtube" || t === "long" || t === "longform") return "youtube";
  if (t === "carousel") return "carousel";
  if (t.startsWith("caption_")) return t;
  return t || "reel";
}

export function countWords(s: string): number {
  if (!s) return 0;
  return s.trim().split(/\s+/).filter(Boolean).length;
}
