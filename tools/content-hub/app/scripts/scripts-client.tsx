"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, ChevronRight, X, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ScheduledScript, UnscheduledScript } from "./page";

// ─── helpers ────────────────────────────────────────────────────────────────

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function formatDayHeader(iso: string, label: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return `${label} ${d.getUTCDate()}`;
}

function formatWeekRange(monday: string, sunday: string): string {
  const m = new Date(monday + "T00:00:00Z");
  const s = new Date(sunday + "T00:00:00Z");
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-AU", {
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  return `${fmt(m)} – ${fmt(s)}`;
}

function slotLabel(slotType: string): string {
  const map: Record<string, string> = {
    reel_1: "Reel 1",
    reel_2: "Reel 2",
    youtube: "YouTube",
    carousel: "Carousel",
    fb_post: "FB Post",
  };
  return map[slotType] ?? slotType;
}

const STATUS_OPTIONS = [
  "new",
  "picked",
  "bookmarked",
  "dismissed",
  "scripted",
  "filmed",
  "edited",
  "posted",
];

// ─── Drawer ──────────────────────────────────────────────────────────────────

type DrawerItem =
  | { kind: "scheduled"; data: ScheduledScript }
  | { kind: "unscheduled"; data: UnscheduledScript };

function Drawer({
  item,
  onClose,
  onSaved,
}: {
  item: DrawerItem;
  onClose: () => void;
  onSaved: (ideaId: number, notes: string, status: string) => void;
}) {
  const ideaId =
    item.kind === "scheduled" ? item.data.ideaId : item.data.ideaId;
  const initialNotes =
    item.kind === "scheduled" ? item.data.notes ?? "" : item.data.notes ?? "";
  const initialStatus =
    item.kind === "scheduled" ? item.data.ideaStatus : item.data.status;
  const reelBody =
    item.kind === "scheduled" ? item.data.reelBody : item.data.reelBody;
  const title =
    item.kind === "scheduled" ? item.data.title : item.data.title;

  const [notes, setNotes] = useState(initialNotes);
  const [status, setStatus] = useState(initialStatus);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    const res = await fetch(`/api/ideas/${ideaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes, status }),
    });
    setSaving(false);
    if (!res.ok) {
      setError("Save failed.");
      return;
    }
    setSaved(true);
    onSaved(ideaId, notes, status);
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <aside className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-background border-l shadow-xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 py-4 border-b shrink-0">
          <div className="flex flex-col gap-1 min-w-0">
            <p className="text-sm font-semibold leading-snug truncate">{title}</p>
            {item.kind === "scheduled" && (
              <div className="flex gap-1.5 flex-wrap">
                <Badge variant="outline" className="text-xs">
                  {slotLabel(item.data.slotType)}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {item.data.slotDate}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {item.data.status}
                </Badge>
              </div>
            )}
            {item.kind === "unscheduled" && item.data.pillar && (
              <Badge variant="secondary" className="text-xs w-fit">
                {item.data.pillar}
              </Badge>
            )}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 text-muted-foreground hover:text-foreground"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-5">
          {/* Reel script */}
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Reel script
            </p>
            {reelBody ? (
              <p className="text-sm whitespace-pre-wrap leading-relaxed bg-muted/40 rounded-lg p-3">
                {reelBody}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No reel script yet — open the full editor to generate one.
              </p>
            )}
          </div>

          {/* Status */}
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Status
            </p>
            <Select value={status} onValueChange={(v) => v && setStatus(v)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Notes
            </p>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reviewer notes, filming reminders…"
              rows={5}
              className="resize-y text-sm"
            />
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
          {saved && (
            <p className="text-xs text-green-500">Saved.</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-t shrink-0">
          <Link
            href={`/scripts/${ideaId}`}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ExternalLink size={14} />
            Full editor
          </Link>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </aside>
    </>
  );
}

// ─── Card ────────────────────────────────────────────────────────────────────

function ScriptCard({
  title,
  pillar,
  slotType,
  status,
  hasReel,
  onClick,
}: {
  title: string;
  pillar?: string | null;
  slotType?: string;
  status: string;
  hasReel: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border bg-card p-3 hover:bg-muted/30 transition-colors flex flex-col gap-1.5"
    >
      <p className="text-sm font-medium leading-snug line-clamp-2">{title}</p>
      <div className="flex flex-wrap gap-1">
        {slotType && (
          <Badge variant="outline" className="text-xs">
            {slotLabel(slotType)}
          </Badge>
        )}
        {pillar && (
          <Badge variant="secondary" className="text-xs">
            {pillar}
          </Badge>
        )}
        <Badge variant="outline" className="text-xs">
          {status}
        </Badge>
        {!hasReel && (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            no reel
          </Badge>
        )}
      </div>
    </button>
  );
}

// ─── Main client component ────────────────────────────────────────────────────

export function ScriptsClient({
  monday,
  sunday,
  scheduled,
  unscheduled,
}: {
  monday: string;
  sunday: string;
  scheduled: ScheduledScript[];
  unscheduled: UnscheduledScript[];
}) {
  const router = useRouter();

  // Local state for notes/status after drawer saves (optimistic)
  const [overrides, setOverrides] = useState<
    Record<number, { notes: string; status: string }>
  >({});

  const [drawerItem, setDrawerItem] = useState<DrawerItem | null>(null);

  // Week navigation
  function navigate(direction: -1 | 1) {
    const newMonday = addDays(monday, direction * 7);
    router.push(`/scripts?week=${newMonday}`);
  }

  // Build day array
  const days = DAY_LABELS.map((label, i) => ({
    label,
    iso: addDays(monday, i),
  }));

  // Group scheduled by date
  const byDate = new Map<string, ScheduledScript[]>();
  for (const s of scheduled) {
    const list = byDate.get(s.slotDate) ?? [];
    list.push(s);
    byDate.set(s.slotDate, list);
  }

  const handleSaved = useCallback(
    (ideaId: number, notes: string, status: string) => {
      setOverrides((prev) => ({ ...prev, [ideaId]: { notes, status } }));
    },
    [],
  );

  const openScheduled = (item: ScheduledScript) => {
    const override = overrides[item.ideaId];
    setDrawerItem({
      kind: "scheduled",
      data: override
        ? { ...item, notes: override.notes, ideaStatus: override.status }
        : item,
    });
  };

  const openUnscheduled = (item: UnscheduledScript) => {
    const override = overrides[item.ideaId];
    setDrawerItem({
      kind: "unscheduled",
      data: override
        ? { ...item, notes: override.notes, status: override.status }
        : item,
    });
  };

  const totalScheduled = scheduled.length;
  const totalUnscheduled = unscheduled.length;

  return (
    <>
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Scripts</h1>
          <p className="text-sm text-muted-foreground">
            {totalScheduled} scheduled · {totalUnscheduled} unscheduled
          </p>
        </div>

        {/* Week navigator */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
            aria-label="Previous week"
          >
            <ChevronLeft size={16} />
          </Button>
          <p className="text-sm font-medium flex-1 text-center">
            {formatWeekRange(monday, sunday)}
          </p>
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(1)}
            aria-label="Next week"
          >
            <ChevronRight size={16} />
          </Button>
        </div>

        {/* Day sections */}
        <div className="flex flex-col gap-4">
          {days.map(({ label, iso }) => {
            const dayItems = byDate.get(iso) ?? [];
            return (
              <div key={iso} className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground w-16">
                    {formatDayHeader(iso, label)}
                  </p>
                  <div className="flex-1 h-px bg-border" />
                  {dayItems.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {dayItems.length}
                    </span>
                  )}
                </div>
                {dayItems.length === 0 ? (
                  <p className="text-xs text-muted-foreground pl-1 italic">
                    Nothing scheduled
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {dayItems.map((item) => {
                      const override = overrides[item.ideaId];
                      return (
                        <ScriptCard
                          key={item.scheduleId}
                          title={item.title}
                          pillar={item.pillar}
                          slotType={item.slotType}
                          status={override?.status ?? item.ideaStatus}
                          hasReel={!!item.reelBody}
                          onClick={() => openScheduled(item)}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Unscheduled section */}
        {totalUnscheduled > 0 && (
          <div className="flex flex-col gap-3 pt-2">
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Unscheduled
              </p>
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-muted-foreground">
                {totalUnscheduled}
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {unscheduled.map((item) => {
                const override = overrides[item.ideaId];
                return (
                  <ScriptCard
                    key={item.ideaId}
                    title={item.title}
                    pillar={item.pillar}
                    status={override?.status ?? item.status}
                    hasReel={!!item.reelBody}
                    onClick={() => openUnscheduled(item)}
                  />
                );
              })}
            </div>
          </div>
        )}

        {totalScheduled === 0 && totalUnscheduled === 0 && (
          <p className="text-sm text-muted-foreground">
            No scripts this week and none unscheduled. Pick an idea in{" "}
            <Link href="/ideation" className="underline">
              Ideation
            </Link>
            .
          </p>
        )}
      </div>

      {/* Slide-in drawer */}
      {drawerItem && (
        <Drawer
          item={drawerItem}
          onClose={() => setDrawerItem(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
