"use client";

import * as React from "react";
import {
  DndContext,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  addMonths,
  endOfMonth,
  format,
  isSameDay,
  startOfMonth,
  startOfWeek,
  addDays,
} from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type Slot = {
  id: number;
  script_id: number | null;
  slot_date: string; // YYYY-MM-DD
  slot_type: string;
  pillar: string | null;
  status: string;
  notes: string | null;
  script_body: string | null;
  idea_title: string | null;
};

const STATUS_STYLES: Record<string, string> = {
  planned: "bg-muted text-muted-foreground border-border",
  scripted: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  filmed: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  edited: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  posted: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

const STATUSES = ["planned", "scripted", "filmed", "edited", "posted"];

const SLOT_LABEL: Record<string, string> = {
  reel_1: "R1",
  reel_2: "R2",
  youtube: "YT",
  carousel: "CA",
  fb_post: "FB",
};

function ymd(d: Date): string {
  return format(d, "yyyy-MM-dd");
}

function DraggableSlot({
  slot,
  onClick,
}: {
  slot: Slot;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `slot-${slot.id}`,
    data: { slot },
  });
  const cls = STATUS_STYLES[slot.status] ?? STATUS_STYLES.planned;
  const topic = slot.notes ?? slot.idea_title ?? "";
  return (
    <button
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      type="button"
      onClick={(e) => {
        // Only open dialog if not actively dragging
        if (!isDragging) onClick();
        e.stopPropagation();
      }}
      className={cn(
        "w-full text-left rounded border px-1.5 py-0.5 text-[10px] leading-tight truncate cursor-grab active:cursor-grabbing",
        cls,
        isDragging && "opacity-40",
      )}
      title={topic}
    >
      <span className="font-mono font-semibold mr-1">
        {SLOT_LABEL[slot.slot_type] ?? slot.slot_type}
      </span>
      <span className="truncate">{topic || "—"}</span>
    </button>
  );
}

function DayCell({
  date,
  inMonth,
  isToday,
  slots,
  onSlotClick,
}: {
  date: Date;
  inMonth: boolean;
  isToday: boolean;
  slots: Slot[];
  onSlotClick: (slot: Slot) => void;
}) {
  const id = ymd(date);
  const { setNodeRef, isOver } = useDroppable({ id: `day-${id}`, data: { date: id } });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "min-h-[96px] border border-border p-1.5 flex flex-col gap-1 transition-colors",
        !inMonth && "bg-muted/30 text-muted-foreground/50",
        isOver && "bg-muted/60",
      )}
      style={
        isToday
          ? { borderColor: "var(--brand, #02B3E9)", borderWidth: 2 }
          : undefined
      }
    >
      <div
        className={cn(
          "text-[11px] font-mono font-semibold",
          isToday && "text-[color:var(--brand,#02B3E9)]",
        )}
      >
        {format(date, "d")}
      </div>
      <div className="flex flex-col gap-1">
        {slots.map((s) => (
          <DraggableSlot key={s.id} slot={s} onClick={() => onSlotClick(s)} />
        ))}
      </div>
    </div>
  );
}

export function CalendarGrid({ initialSlots }: { initialSlots: Slot[] }) {
  const today = React.useMemo(() => new Date(), []);
  const [cursor, setCursor] = React.useState<Date>(startOfMonth(today));
  const [slots, setSlots] = React.useState<Slot[]>(initialSlots);
  const [activeSlot, setActiveSlot] = React.useState<Slot | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  const monthStart = startOfMonth(cursor);
  const monthEnd = endOfMonth(cursor);
  const gridStart = startOfWeek(monthStart, { weekStartsOn: 0 });

  // Fetch when cursor changes
  React.useEffect(() => {
    const year = cursor.getFullYear();
    const month = cursor.getMonth() + 1;
    fetch(`/api/schedule?year=${year}&month=${month}`)
      .then((r) => r.json())
      .then((data) => setSlots(data.slots ?? []))
      .catch(() => {});
  }, [cursor]);

  const slotsByDate = React.useMemo(() => {
    const m = new Map<string, Slot[]>();
    for (const s of slots) {
      const arr = m.get(s.slot_date) ?? [];
      arr.push(s);
      m.set(s.slot_date, arr);
    }
    return m;
  }, [slots]);

  const days: Date[] = [];
  for (let i = 0; i < 42; i++) days.push(addDays(gridStart, i));

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const slot = (active.data.current as { slot: Slot } | undefined)?.slot;
    const newDate = (over.data.current as { date: string } | undefined)?.date;
    if (!slot || !newDate || slot.slot_date === newDate) return;
    // optimistic
    setSlots((prev) =>
      prev.map((s) => (s.id === slot.id ? { ...s, slot_date: newDate } : s)),
    );
    try {
      await fetch(`/api/schedule/${slot.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot_date: newDate }),
      });
    } catch {
      // rollback
      setSlots((prev) =>
        prev.map((s) =>
          s.id === slot.id ? { ...s, slot_date: slot.slot_date } : s,
        ),
      );
    }
  };

  const updateStatus = async (status: string) => {
    if (!activeSlot) return;
    setSlots((prev) =>
      prev.map((s) => (s.id === activeSlot.id ? { ...s, status } : s)),
    );
    setActiveSlot({ ...activeSlot, status });
    await fetch(`/api/schedule/${activeSlot.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  };

  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => setCursor(addMonths(cursor, -1))}
          >
            <ChevronLeft />
          </Button>
          <div className="text-lg font-semibold min-w-[180px] text-center">
            {format(cursor, "MMMM yyyy")}
          </div>
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => setCursor(addMonths(cursor, 1))}
          >
            <ChevronRight />
          </Button>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCursor(startOfMonth(new Date()))}
        >
          Today
        </Button>
      </div>

      <div className="grid grid-cols-7 gap-0 mb-1">
        {weekdays.map((d) => (
          <div
            key={d}
            className="text-[11px] text-muted-foreground font-mono uppercase tracking-wider px-2 py-1"
          >
            {d}
          </div>
        ))}
      </div>

      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-7 gap-0">
          {days.map((d) => {
            const inMonth = d >= monthStart && d <= monthEnd;
            const isToday = isSameDay(d, today);
            const daySlots = slotsByDate.get(ymd(d)) ?? [];
            return (
              <DayCell
                key={ymd(d)}
                date={d}
                inMonth={inMonth}
                isToday={isToday}
                slots={daySlots}
                onSlotClick={(s) => setActiveSlot(s)}
              />
            );
          })}
        </div>
      </DndContext>

      <Dialog
        open={!!activeSlot}
        onOpenChange={(open) => !open && setActiveSlot(null)}
      >
        <DialogContent>
          {activeSlot && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {SLOT_LABEL[activeSlot.slot_type] ?? activeSlot.slot_type} —{" "}
                  {activeSlot.slot_date}
                </DialogTitle>
                <DialogDescription>
                  {activeSlot.notes ?? activeSlot.idea_title ?? "No topic"}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-20">
                    Status
                  </span>
                  <Select
                    value={activeSlot.status}
                    onValueChange={(v) => updateStatus(String(v))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUSES.map((s) => (
                        <SelectItem key={s} value={s}>
                          {s}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-20">
                    Script
                  </span>
                  {activeSlot.script_id ? (
                    <a
                      href={`/scripts/${activeSlot.script_id}`}
                      className="text-sm underline text-[color:var(--brand,#02B3E9)]"
                    >
                      View script #{activeSlot.script_id}
                    </a>
                  ) : (
                    <Badge variant="outline">unlinked</Badge>
                  )}
                </div>
                {activeSlot.pillar && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-20">
                      Pillar
                    </span>
                    <Badge variant="secondary">{activeSlot.pillar}</Badge>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
