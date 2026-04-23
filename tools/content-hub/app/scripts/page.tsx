export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { ScriptsClient } from "./scripts-client";

export type ScheduledScript = {
  scheduleId: number;
  scriptId: number;
  ideaId: number;
  slotDate: string;
  slotType: string;
  status: string;
  pillar: string | null;
  title: string;
  reelBody: string | null;
  notes: string | null;
  ideaStatus: string;
  hasCarousel: boolean;
};

export type KanbanIdea = {
  ideaId: number;
  title: string;
  hook: string | null;
  pillar: string | null;
  modeledAfter: string | null;
  status: string;
  notes: string | null;
  scriptId: number | null;
  reelBody: string | null;
  hasCarousel: boolean;
};

function weekMonday(date: Date): Date {
  const d = new Date(date);
  d.setUTCHours(0, 0, 0, 0);
  const day = d.getUTCDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setUTCDate(d.getUTCDate() + diff);
  return d;
}

function toISO(d: Date) {
  return d.toISOString().slice(0, 10);
}

export default async function ScriptsPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string }>;
}) {
  const sp = await searchParams;
  const weekParam = sp.week;

  const anchor =
    weekParam && /^\d{4}-\d{2}-\d{2}$/.test(weekParam)
      ? weekMonday(new Date(weekParam + "T00:00:00Z"))
      : weekMonday(new Date());

  const mondayStr = toISO(anchor);
  const sundayDate = new Date(anchor);
  sundayDate.setUTCDate(anchor.getUTCDate() + 6);
  const sundayStr = toISO(sundayDate);

  type RawScheduled = {
    scheduleId: number;
    scriptId: number;
    ideaId: number;
    slotDate: string;
    slotType: string;
    status: string;
    pillar: string | null;
    title: string;
    reelBody: string | null;
    notes: string | null;
    ideaStatus: string;
    carousel_count: number;
  };

  const rawScheduled = db
    .prepare(
      `SELECT
         sc.id           AS scheduleId,
         sc.script_id    AS scriptId,
         sc.slot_date    AS slotDate,
         sc.slot_type    AS slotType,
         sc.status       AS status,
         sc.pillar       AS pillar,
         COALESCE(sc.notes, i.title) AS title,
         s.body          AS reelBody,
         i.id            AS ideaId,
         i.notes         AS notes,
         i.status        AS ideaStatus,
         (SELECT COUNT(*) FROM scripts cs WHERE cs.idea_id = i.id AND cs.variant = 'carousel') AS carousel_count
       FROM schedule sc
       LEFT JOIN scripts s  ON s.id = sc.script_id
       LEFT JOIN ideas   i  ON i.id = s.idea_id
       WHERE sc.slot_date >= ? AND sc.slot_date <= ?
         AND sc.slot_type IN ('reel_1','reel_2','youtube','carousel','fb_post')
       ORDER BY sc.slot_date ASC, sc.slot_type ASC`,
    )
    .all(mondayStr, sundayStr) as RawScheduled[];

  const scheduled: ScheduledScript[] = rawScheduled.map((r) => ({
    ...r,
    hasCarousel: r.carousel_count > 0,
  }));

  type RawKanban = {
    idea_id: number;
    title: string;
    hook: string | null;
    pillar: string | null;
    modeled_after: string | null;
    status: string;
    notes: string | null;
    script_id: number | null;
    reel_body: string | null;
    carousel_count: number;
  };

  const rawKanban = db
    .prepare(
      `SELECT
         i.id            AS idea_id,
         i.title,
         i.hook,
         i.pillar,
         i.modeled_after,
         i.status,
         i.notes,
         s.id            AS script_id,
         s.body          AS reel_body,
         (SELECT COUNT(*) FROM scripts cs WHERE cs.idea_id = i.id AND cs.variant = 'carousel') AS carousel_count
       FROM ideas i
       LEFT JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
       ORDER BY i.id DESC`,
    )
    .all() as RawKanban[];

  const kanbanIdeas: KanbanIdea[] = rawKanban.map((r) => ({
    ideaId: r.idea_id,
    title: r.title,
    hook: r.hook,
    pillar: r.pillar,
    modeledAfter: r.modeled_after,
    status: r.status,
    notes: r.notes,
    scriptId: r.script_id,
    reelBody: r.reel_body,
    hasCarousel: r.carousel_count > 0,
  }));

  return (
    <ScriptsClient
      monday={mondayStr}
      sunday={sundayStr}
      scheduled={scheduled}
      kanbanIdeas={kanbanIdeas}
    />
  );
}
