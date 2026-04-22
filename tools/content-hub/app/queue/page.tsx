import db from "@/lib/db";
import { QueueClient, QueueSlot, Caption } from "./queue-client";

export default async function QueuePage() {
  const slots = db
    .prepare(
      `SELECT sch.id AS schedule_id, sch.slot_date, sch.slot_type, sch.status, sch.notes,
              i.id AS idea_id, i.title, i.pillar
       FROM schedule sch
       LEFT JOIN scripts s ON s.id = sch.script_id
       LEFT JOIN ideas i ON i.id = s.idea_id
       WHERE sch.status NOT IN ('posted')
         AND sch.slot_date >= date('now', '-1 day')
       ORDER BY sch.slot_date ASC,
         CASE sch.slot_type
           WHEN 'reel_1'   THEN 0
           WHEN 'reel_2'   THEN 1
           WHEN 'carousel' THEN 2
           WHEN 'youtube'  THEN 3
           ELSE 4
         END`,
    )
    .all() as Omit<QueueSlot, "captions">[];

  const captionStmt = db.prepare(
    `SELECT variant, body FROM scripts
     WHERE idea_id = ?
       AND variant IN ('caption_ig','caption_fb','caption_tiktok','caption_yt','caption_x')
     ORDER BY CASE variant
       WHEN 'caption_ig'      THEN 0
       WHEN 'caption_tiktok'  THEN 1
       WHEN 'caption_yt'      THEN 2
       WHEN 'caption_x'       THEN 3
       ELSE 4
     END`,
  );

  const slotsWithCaptions: QueueSlot[] = slots.map((slot) => ({
    ...slot,
    captions: slot.idea_id
      ? (captionStmt.all(slot.idea_id) as Caption[])
      : [],
  }));

  const readyCount = slotsWithCaptions.filter(
    (s) => s.status === "filmed" || s.status === "edited",
  ).length;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Post Queue</h1>
          <p className="text-sm text-muted-foreground pt-1">
            {slotsWithCaptions.length} scheduled ·{" "}
            <span style={{ color: "#22c55e" }}>{readyCount} ready to post</span>
            {" "}· captions ready to copy
          </p>
        </div>
      </div>

      <QueueClient slots={slotsWithCaptions} />
    </div>
  );
}
