import db from "@/lib/db";
import { IdeationClient } from "./ideation-client";

type IdeaRow = {
  id: number;
  title: string;
  pillar: string | null;
  lane: string | null;
  modeled_after: string | null;
  status: string;
  day_of_week: string | null;
  slot: number | null;
  batch: string | null;
  script_count: number;
  preview: string | null;
};

export default async function IdeationPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; pillar?: string }>;
}) {
  const sp = await searchParams;
  const status = sp.status ?? "all";
  const pillar = sp.pillar ?? "all";

  const where: string[] = [];
  const params: unknown[] = [];
  if (status !== "all") {
    where.push("i.status = ?");
    params.push(status);
  }
  if (pillar !== "all") {
    where.push("i.pillar = ?");
    params.push(pillar);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const ideas = db
    .prepare(
      `SELECT i.id, i.title, i.pillar, i.lane, i.modeled_after, i.status,
              i.day_of_week, i.slot, i.batch,
              (SELECT COUNT(*) FROM scripts s WHERE s.idea_id = i.id) AS script_count,
              (SELECT substr(s.body, 1, 160) FROM scripts s WHERE s.idea_id = i.id ORDER BY s.id LIMIT 1) AS preview
       FROM ideas i
       ${whereSql}
       ORDER BY
         CASE i.status WHEN 'new' THEN 0 WHEN 'bookmarked' THEN 1 WHEN 'picked' THEN 2 ELSE 3 END,
         i.batch IS NULL, i.batch,
         i.slot IS NULL, i.slot,
         i.id DESC`,
    )
    .all(...params) as IdeaRow[];

  const pillarRows = db
    .prepare(
      `SELECT DISTINCT pillar FROM ideas WHERE pillar IS NOT NULL AND pillar != '' ORDER BY pillar`,
    )
    .all() as { pillar: string }[];
  const pillars = pillarRows.map((r) => r.pillar);

  return (
    <IdeationClient
      ideas={ideas}
      pillars={pillars}
      status={status}
      pillar={pillar}
    />
  );
}
