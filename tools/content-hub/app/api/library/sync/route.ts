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

function deriveTitle(key: string): string {
  const filename = key.split("/").pop() ?? key;
  const base = filename.replace(/\.[^.]+$/, "");
  return base.replace(/^[\d-]+/, "").replace(/[_-]+/g, " ").trim() || filename;
}

export async function POST() {
  const bucket = process.env.R2_BUCKET_NAME!;
  const publicBase = process.env.R2_PUBLIC_URL!;

  const existing = db.prepare("SELECT path FROM assets").all() as { path: string }[];
  const existingPaths = new Set(existing.map((r) => r.path));

  let inserted = 0;
  let skipped = 0;
  let scanned = 0;
  let token: string | undefined = undefined;

  const insert = db.prepare(
    "INSERT OR IGNORE INTO assets (path, type, title, url) VALUES (?, ?, ?, ?)",
  );

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
      if (existingPaths.has(key)) {
        skipped += 1;
        continue;
      }
      const type = deriveType(key);
      const title = deriveTitle(key);
      const url = `${publicBase}/${key}`;
      const info = insert.run(key, type, title, url);
      if (info.changes > 0) inserted += 1;
      existingPaths.add(key);
      if (scanned >= 2000) break;
    }
    token = resp.IsTruncated ? resp.NextContinuationToken : undefined;
    if (scanned >= 2000) break;
  } while (token);

  return NextResponse.json({ ok: true, scanned, inserted, skipped });
}
