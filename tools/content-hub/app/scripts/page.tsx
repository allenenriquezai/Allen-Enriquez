import Link from "next/link";
import db from "@/lib/db";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type GroupRow = {
  id: number;
  title: string;
  pillar: string | null;
  status: string;
  variants: string; // comma-joined list from SQLite GROUP_CONCAT
  script_count: number;
};

export default async function ScriptsPage() {
  const rows = db
    .prepare(
      `SELECT i.id, i.title, i.pillar, i.status,
              COALESCE(GROUP_CONCAT(s.variant), '') AS variants,
              COUNT(s.id) AS script_count
       FROM ideas i
       LEFT JOIN scripts s ON s.idea_id = i.id
       WHERE i.status IN ('picked','bookmarked','new')
       GROUP BY i.id
       HAVING script_count > 0 OR i.status = 'picked'
       ORDER BY
         CASE i.status WHEN 'picked' THEN 0 WHEN 'bookmarked' THEN 1 ELSE 2 END,
         i.id DESC`,
    )
    .all() as GroupRow[];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Scripts</h1>
        <p className="text-sm text-muted-foreground">
          {rows.length} idea{rows.length === 1 ? "" : "s"} with scripts
        </p>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No scripts yet. Pick an idea in{" "}
          <Link href="/ideation" className="underline">
            Ideation
          </Link>
          .
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {rows.map((r) => {
            const variants = r.variants
              ? r.variants.split(",").filter(Boolean)
              : [];
            return (
              <Link
                key={r.id}
                href={`/scripts/${r.id}`}
                className="block transition-colors hover:bg-muted/30 rounded-xl"
              >
                <Card>
                  <CardHeader className="pb-0">
                    <CardTitle className="text-base">{r.title}</CardTitle>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {r.pillar && (
                        <Badge variant="secondary">{r.pillar}</Badge>
                      )}
                      <Badge variant="outline">{r.status}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1.5">
                      {variants.length === 0 ? (
                        <span className="text-xs text-muted-foreground">
                          No variants yet — open to generate.
                        </span>
                      ) : (
                        variants.map((v) => (
                          <Badge key={v} variant="outline">
                            {v}
                          </Badge>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
