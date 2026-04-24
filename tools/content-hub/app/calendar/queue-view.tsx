import db from "@/lib/db";
import { QueueClient, type QueueSlot, type Caption } from "@/app/queue/queue-client";

export function QueueView() {
  const slots = db
    .prepare(
      `SELECT sch.id AS schedule_id, sch.slot_date, sch.slot_type, sch.status, sch.notes,
              i.id AS idea_id, i.title, i.pillar,
              sch.asset_id, a.url AS asset_url, a.title AS asset_title, a.type AS asset_type
       FROM schedule sch
       LEFT JOIN scripts s ON s.id = sch.script_id
       LEFT JOIN ideas i ON i.id = s.idea_id
       LEFT JOIN assets a ON a.id = sch.asset_id
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
    .all() as Omit<QueueSlot, "captions" | "reel_body">[];

  const captionStmt = db.prepare(
    `SELECT variant, body FROM scripts
     WHERE idea_id = ?
       AND variant IN ('caption_ig','caption_fb','caption_tiktok','caption_yt','caption_x','caption_linkedin')
     ORDER BY CASE variant
       WHEN 'caption_ig'       THEN 0
       WHEN 'caption_tiktok'   THEN 1
       WHEN 'caption_yt'       THEN 2
       WHEN 'caption_x'        THEN 3
       WHEN 'caption_linkedin' THEN 4
       ELSE 5
     END`,
  );

  const slotsWithCaptions: QueueSlot[] = slots.map((slot) => ({
    ...slot,
    captions: slot.idea_id
      ? (captionStmt.all(slot.idea_id) as Caption[])
      : [],
    reel_body: null,
  }));

  const reelStmt = db.prepare(
    `SELECT body FROM scripts WHERE idea_id = ? AND variant = 'reel' LIMIT 1`
  );
  const slotsWithAll: QueueSlot[] = slotsWithCaptions.map((slot) => ({
    ...slot,
    reel_body: slot.idea_id
      ? (reelStmt.get(slot.idea_id) as { body: string } | undefined)?.body ?? null
      : null,
  }));

  const readyCount = slotsWithAll.filter(
    (s) => s.status === "filmed" || s.status === "edited",
  ).length;

  const ytToken = db.prepare("SELECT 1 FROM oauth_tokens WHERE platform = 'youtube'").get();
  const tikToken = db.prepare("SELECT 1 FROM oauth_tokens WHERE platform = 'tiktok'").get();

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground">
        {slotsWithAll.length} scheduled ·{" "}
        <span style={{ color: "#22c55e" }}>{readyCount} ready to post</span>
        {" "}· captions ready to copy
      </p>
      <QueueClient slots={slotsWithAll} ytConnected={!!ytToken} tikConnected={!!tikToken} />
    </div>
  );
}
