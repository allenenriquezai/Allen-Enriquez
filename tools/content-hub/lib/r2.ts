import {
  S3Client,
  PutObjectCommand,
  CopyObjectCommand,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3";
import fs from "node:fs";

let _client: S3Client | null = null;

export function r2Client(): S3Client {
  if (_client) return _client;
  _client = new S3Client({
    region: "auto",
    endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    },
  });
  return _client;
}

export function r2Bucket(): string {
  const bucket = process.env.R2_BUCKET_NAME;
  if (!bucket) throw new Error("R2_BUCKET_NAME not set");
  return bucket;
}

export function r2PublicUrl(key: string): string {
  const base = process.env.R2_PUBLIC_URL;
  if (!base) throw new Error("R2_PUBLIC_URL not set");
  return `${base.replace(/\/$/, "")}/${key.replace(/^\//, "")}`;
}

export async function uploadFile(localPath: string, key: string, contentType?: string): Promise<string> {
  const body = fs.readFileSync(localPath);
  await r2Client().send(
    new PutObjectCommand({
      Bucket: r2Bucket(),
      Key: key,
      Body: body,
      ContentType: contentType ?? guessContentType(key),
    }),
  );
  return r2PublicUrl(key);
}

export async function moveObject(fromKey: string, toKey: string): Promise<string> {
  if (fromKey === toKey) return r2PublicUrl(toKey);
  const bucket = r2Bucket();
  await r2Client().send(
    new CopyObjectCommand({
      Bucket: bucket,
      CopySource: `${bucket}/${encodeURIComponent(fromKey).replace(/%2F/g, "/")}`,
      Key: toKey,
    }),
  );
  await r2Client().send(
    new DeleteObjectCommand({ Bucket: bucket, Key: fromKey }),
  );
  return r2PublicUrl(toKey);
}

export async function deleteObject(key: string): Promise<void> {
  await r2Client().send(
    new DeleteObjectCommand({ Bucket: r2Bucket(), Key: key }),
  );
}

function guessContentType(key: string): string {
  const ext = key.toLowerCase().split(".").pop() ?? "";
  switch (ext) {
    case "mp4": return "video/mp4";
    case "mov": return "video/quicktime";
    case "webm": return "video/webm";
    case "m4v": return "video/x-m4v";
    case "jpg":
    case "jpeg": return "image/jpeg";
    case "png": return "image/png";
    case "webp": return "image/webp";
    case "gif": return "image/gif";
    default: return "application/octet-stream";
  }
}
