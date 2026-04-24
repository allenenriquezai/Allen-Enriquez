export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import db from "@/lib/db";
import { PostView } from "./post-view";
import type { Asset, AssetPost } from "@/components/asset-tile";

type AssetRow = Omit<Asset, "posts">;
type IdeaRow = { id: number; title: string };
type ScriptRow = { id: number; idea_id: number; variant: string; body: string };

export default async function LibraryAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const assetId = Number(id);
  if (!Number.isFinite(assetId)) notFound();

  const row = db.prepare("SELECT * FROM assets WHERE id = ?").get(assetId) as AssetRow | undefined;
  if (!row) notFound();

  const posts = db
    .prepare("SELECT * FROM posts WHERE asset_id = ? ORDER BY posted_at DESC")
    .all(assetId) as AssetPost[];

  const ideas = db
    .prepare("SELECT id, title FROM ideas ORDER BY created_at DESC")
    .all() as IdeaRow[];

  // Preload scripts for the linked idea (if any) so initial captions populate fast
  let initialScripts: ScriptRow[] = [];
  if (row.idea_id) {
    initialScripts = db
      .prepare("SELECT id, idea_id, variant, body FROM scripts WHERE idea_id = ?")
      .all(row.idea_id) as ScriptRow[];
  }

  const asset: Asset = { ...row, posts };

  return <PostView asset={asset} ideas={ideas} initialScripts={initialScripts} />;
}
