export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { type Asset, type AssetPost } from "@/components/asset-tile";
import { LibraryUploadButton } from "@/components/library-upload-button";
import { LibraryGrid } from "@/components/library-grid";

type AssetRow = {
  id: number;
  path: string;
  type: string;
  title: string | null;
  url: string | null;
  idea_id: number | null;
  created_at: string;
};

// Server component — reads assets + posts from SQLite and passes to client component.
export default function LibraryPage() {
  const assetRows = db
    .prepare("SELECT * FROM assets ORDER BY created_at DESC, id DESC")
    .all() as AssetRow[];
  const postRows = db
    .prepare("SELECT * FROM posts ORDER BY posted_at DESC")
    .all() as AssetPost[];

  const postsByAsset = new Map<number, AssetPost[]>();
  for (const p of postRows) {
    const arr = postsByAsset.get(p.asset_id) ?? [];
    arr.push(p);
    postsByAsset.set(p.asset_id, arr);
  }

  const assets: Asset[] = assetRows.map((a) => ({
    ...a,
    posts: postsByAsset.get(a.id) ?? [],
  }));

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Library</h1>
          <p className="text-sm text-muted-foreground">
            Click any asset to post across platforms.
          </p>
        </div>
        <LibraryUploadButton />
      </div>

      <LibraryGrid assets={assets} />
    </div>
  );
}
