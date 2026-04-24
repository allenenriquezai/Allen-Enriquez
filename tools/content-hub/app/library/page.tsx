export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { AssetTile, type Asset, type AssetPost } from "@/components/asset-tile";
import { LibraryUploadButton } from "@/components/library-upload-button";

type AssetRow = {
  id: number;
  path: string;
  type: string;
  title: string | null;
  url: string | null;
  idea_id: number | null;
  created_at: string;
};

// Server component — reads assets + posts from SQLite and renders the grid.
// Each tile manages its own platform-toggle state client-side.
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

  const videos = assets.filter((a) => a.type === "reel" || a.type === "youtube");
  const carousels = assets.filter((a) => a.type === "carousel");

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Library</h1>
          <p className="text-sm text-muted-foreground">
            Produced assets. Click a platform chip to log or unlog a post.
          </p>
        </div>
        <LibraryUploadButton />
      </div>

      <section>
        <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">
          Videos ({videos.length})
        </h2>
        {videos.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No videos yet. Run <code className="font-mono">npm run seed</code>.
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {videos.map((a) => (
              <AssetTile key={a.id} asset={a} />
            ))}
          </div>
        )}
      </section>

      {carousels.length > 0 && (
        <section>
          <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">
            Carousels ({carousels.length})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {carousels.map((a) => (
              <AssetTile key={a.id} asset={a} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
