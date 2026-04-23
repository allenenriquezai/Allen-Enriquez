export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { ScriptsClient } from "./scripts-client";

export type ScheduledScript = {
  scheduleId: number;
  scriptId: number;
  ideaId: number;
  slotDate: string; // YYYY-MM-DD
  slotType: string;
  status: string;
  pillar: string | null;
  title: string;
  reelBody: string | null;
  notes: string | null;
  ideaStatus: string;
};

export type UnscheduledScript = {
  ideaId: number;
  title: string;
  pillar: string | null;
  status: string;
  reelBody: string | null;
  notes: string | null;
};

/** Return Monday of the ISO week containing `date`. */
function weekMonday(date: Date): Date {
  const d = new Date(date);
  d.setUTCHours(0, 0, 0, 0);
  const day = d.getUTCDay(); // 0 = Sun
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

  // Determine anchor Monday
  const anchor =
    weekParam && /^\d{4}-\d{2}-\d{2}$/.test(weekParam)
      ? weekMonday(new Date(weekParam + "T00:00:00Z"))
      : weekMonday(new Date());

  const mondayStr = toISO(anchor);
  const sundayDate = new Date(anchor);
  sundayDate.setUTCDate(anchor.getUTCDate() + 6);
  const sundayStr = toISO(sundayDate);

  // Scheduled reels in the week
  const scheduled = db
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
         i.status        AS ideaStatus
       FROM schedule sc
       LEFT JOIN scripts s  ON s.id = sc.script_id
       LEFT JOIN ideas   i  ON i.id = s.idea_id
       WHERE sc.slot_date >= ? AND sc.slot_date <= ?
         AND sc.slot_type IN ('reel_1','reel_2','youtube','carousel','fb_post')
       ORDER BY sc.slot_date ASC, sc.slot_type ASC`,
    )
    .all(mondayStr, sundayStr) as ScheduledScript[];

  // IDs already in schedule (to exclude from unscheduled)
  const scheduledIdeaIds = new Set(
    scheduled.map((r) => r.ideaId).filter(Boolean),
  );

  // Unscheduled: ideas with a reel script, not yet on any schedule row
  const unscheduled = db
    .prepare(
      `SELECT
         i.id     AS ideaId,
         i.title  AS title,
         i.pillar AS pillar,
         i.status AS status,
         i.notes  AS notes,
         s.body   AS reelBody
       FROM ideas i
       JOIN scripts s ON s.idea_id = i.id AND s.variant = 'reel'
       WHERE i.status IN ('picked','bookmarked','new')
         AND i.id NOT IN (
           SELECT DISTINCT idea_id
           FROM scripts
           JOIN schedule ON schedule.script_id = scripts.id
         )
       ORDER BY
         CASE i.status WHEN 'picked' THEN 0 WHEN 'bookmarked' THEN 1 ELSE 2 END,
         i.id DESC`,
    )
    .all() as UnscheduledScript[];

  // Filter out any that ended up in scheduled (safety net)
  const filteredUnscheduled = unscheduled.filter(
    (u) => !scheduledIdeaIds.has(u.ideaId),
  );

  return (
    <ScriptsClient
      monday={mondayStr}
      sunday={sundayStr}
      scheduled={scheduled}
      unscheduled={filteredUnscheduled}
    />
  );
}
