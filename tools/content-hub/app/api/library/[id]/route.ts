import { NextRequest, NextResponse } from "next/server";
import { S3Client, DeleteObjectCommand } from "@aws-sdk/client-s3";
import db from "@/lib/db";
import { patchAssetRow } from "../route";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json();
  return patchAssetRow(Number(id), body);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const url = new URL(req.url);
  const deleteR2 = url.searchParams.get("r2") === "1";

  const asset = db
    .prepare("SELECT id, path FROM assets WHERE id = ?")
    .get(Number(id)) as { id: number; path: string } | undefined;
  if (!asset) return NextResponse.json({ error: "not found" }, { status: 404 });

  let r2_deleted = false;
  let r2_error: string | null = null;

  if (deleteR2 && process.env.R2_BUCKET_NAME) {
    try {
      const s3 = new S3Client({
        region: "auto",
        endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
        credentials: {
          accessKeyId: process.env.R2_ACCESS_KEY_ID!,
          secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
        },
      });
      await s3.send(
        new DeleteObjectCommand({
          Bucket: process.env.R2_BUCKET_NAME,
          Key: asset.path,
        }),
      );
      r2_deleted = true;
    } catch (e) {
      r2_error = e instanceof Error ? e.message : String(e);
    }
  }

  db.prepare("DELETE FROM posts WHERE asset_id = ?").run(asset.id);
  db.prepare("DELETE FROM assets WHERE id = ?").run(asset.id);

  return NextResponse.json({ ok: true, id: asset.id, r2_deleted, r2_error });
}
