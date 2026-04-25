import { NextResponse } from "next/server";
import { S3Client, ListObjectsV2Command, type ListObjectsV2CommandOutput } from "@aws-sdk/client-s3";
import db from "@/lib/db";

const s3 = new S3Client({
  region: "auto",
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});

const VIDEO_EXT = new Set(["mp4", "mov", "m4v", "webm"]);
const IMAGE_EXT = new Set(["jpg", "jpeg", "png", "webp", "gif"]);

function deriveType(key: string): string {
  const lower = key.toLowerCase();
  const ext = lower.split(".").pop() ?? "";
  if (VIDEO_EXT.has(ext)) {
    if (lower.includes("youtube") || lower.includes("/yt/")) return "youtube";
    return "reel";
  }
  if (IMAGE_EXT.has(ext)) {
    if (lower.includes("thumb")) return "thumbnail";
    return "carousel";
  }
  return "reel";
}

const GENERIC_NAMES = new Set([
  "final", "draft", "source", "render", "design", "raw", "edit", "edited",
  "export", "output", "video", "clip",
]);
const VARIANT_RE = /\b(v\d+(?:\.\d+)?|draft|final|wip|raw|export|edit(?:ed)?)\b/gi;

function titleCase(s: string): string {
  return s
    .split(/\s+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function cleanSegment(s: string): string {
  return s
    .replace(/\.[^.]+$/, "")              // strip extension
    .replace(/^\d{4,}[-_ ]+/, "")          // strip 4+ digit timestamp prefix only
    .replace(/[_-]+/g, " ")                // dashes/underscores → spaces
    .replace(/\s+/g, " ")
    .trim();
}

// Returns [title, variant_label].
export function deriveTitleParts(key: string): [string, string | null] {
  const segments = key.split("/").filter(Boolean);
  const filename = segments[segments.length - 1] ?? key;
  let base = cleanSegment(filename);

  // If filename is generic (final, draft, source...), use parent folder.
  const lowerBase = base.toLowerCase();
  if (
    GENERIC_NAMES.has(lowerBase) ||
    lowerBase.startsWith("final ") ||
    lowerBase.startsWith("draft ") ||
    lowerBase.startsWith("design ") ||
    /^(?:final|draft|raw|design|render|edit)\s*v?\d/.test(lowerBase)
  ) {
    // walk up until we find a non-generic, non-render-bucket folder
    for (let i = segments.length - 2; i >= 0; i--) {
      const seg = cleanSegment(segments[i]);
      const lower = seg.toLowerCase();
      if (!seg) continue;
      if (["renders", "render", "assets", "exports", "export", "output", "videos", "personal", "projects", "uploads", "upload", "ready", "drafts", "draft"].includes(lower)) continue;
      base = seg;
      break;
    }
  }

  // Extract variant labels (v1, v2, draft, final...) into separate field.
  const variants: string[] = [];
  base = base
    .replace(VARIANT_RE, (m) => {
      variants.push(m.toLowerCase());
      return "";
    })
    .replace(/\s+/g, " ")
    .trim();

  if (!base) base = cleanSegment(filename);

  const title = titleCase(base);
  const variant_label = variants.length ? variants.join(" ") : null;
  return [title || filename, variant_label];
}

// Heuristic: did the existing title look auto-generated and stale?
function isGenericTitle(title: string | null): boolean {
  if (!title) return true;
  const t = title.trim().toLowerCase();
  if (GENERIC_NAMES.has(t)) return true;
  if (["uploads", "upload", "ready", "asset", "test", "untitled"].includes(t)) return true;
  if (/^asset\d+$/.test(t)) return true;
  if (/^(final|draft|design|render|raw|edit)\s*v?\d/.test(t)) return true;
  return false;
}

export async function POST() {
  const bucket = process.env.R2_BUCKET_NAME!;
  const publicBase = process.env.R2_PUBLIC_URL!;

  type ExistingRow = { path: string; title: string | null };
  const existing = db
    .prepare("SELECT path, title FROM assets")
    .all() as ExistingRow[];
  const existingByPath = new Map(existing.map((r) => [r.path, r]));

  let inserted = 0;
  let skipped = 0;
  let scanned = 0;
  let cleaned = 0;
  let token: string | undefined = undefined;

  const insert = db.prepare(
    "INSERT OR IGNORE INTO assets (path, type, title, url, variant_label) VALUES (?, ?, ?, ?, ?)",
  );
  const updateTitle = db.prepare(
    "UPDATE assets SET title = ?, variant_label = ? WHERE path = ?",
  );

  // Clean existing rows whose titles look generic (filename-only).
  for (const row of existing) {
    if (isGenericTitle(row.title)) {
      const [t, v] = deriveTitleParts(row.path);
      if (t !== row.title) {
        updateTitle.run(t, v, row.path);
        cleaned += 1;
      }
    }
  }

  do {
    const resp: ListObjectsV2CommandOutput = await s3.send(
      new ListObjectsV2Command({
        Bucket: bucket,
        ContinuationToken: token,
        MaxKeys: 1000,
      }),
    );
    for (const obj of resp.Contents ?? []) {
      scanned += 1;
      const key = obj.Key;
      if (!key) continue;
      if (existingByPath.has(key)) {
        skipped += 1;
        continue;
      }
      const type = deriveType(key);
      const [title, variant_label] = deriveTitleParts(key);
      const url = `${publicBase}/${key}`;
      const info = insert.run(key, type, title, url, variant_label);
      if (info.changes > 0) inserted += 1;
      existingByPath.set(key, { path: key, title });
      if (scanned >= 2000) break;
    }
    token = resp.IsTruncated ? resp.NextContinuationToken : undefined;
    if (scanned >= 2000) break;
  } while (token);

  return NextResponse.json({ ok: true, scanned, inserted, skipped, cleaned });
}
