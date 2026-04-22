import db from "@/lib/db";
import { CalendarGrid, type Slot } from "@/components/calendar-grid";

// Server component — loads current month's slots from SQLite and hands off
// to the client grid for drag-drop + dialog interactions.
export default function CalendarPage() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const end = `${nextYear}-${String(nextMonth).padStart(2, "0")}-01`;

  const slots = db
    .prepare(
      `SELECT s.id, s.script_id, s.slot_date, s.slot_type, s.pillar, s.status, s.notes,
              sc.body AS script_body,
              i.title AS idea_title
       FROM schedule s
       LEFT JOIN scripts sc ON sc.id = s.script_id
       LEFT JOIN ideas i ON i.id = sc.idea_id
       WHERE s.slot_date >= ? AND s.slot_date < ?
       ORDER BY s.slot_date ASC, s.slot_type ASC`,
    )
    .all(start, end) as Slot[];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Calendar</h1>
        <p className="text-sm text-muted-foreground">
          Drag slot pills between days to reschedule. Click a pill for details.
        </p>
      </div>
      <CalendarGrid initialSlots={slots} />
    </div>
  );
}
