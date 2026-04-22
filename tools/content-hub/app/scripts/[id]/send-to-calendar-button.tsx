"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Calendar } from "lucide-react";

function today() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export function SendToCalendarButton({
  ideaId,
  title,
  scriptIds,
  pillar,
}: {
  ideaId: number;
  title: string;
  scriptIds: { variant: string; id: number }[];
  pillar: string | null;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [slotDate, setSlotDate] = useState(today());
  const [slotType, setSlotType] = useState("reel_1");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reelScript = scriptIds.find((s) => s.variant === "reel");
  const ytScript = scriptIds.find((s) => s.variant === "youtube");

  async function handleSave() {
    setSaving(true);
    setError(null);
    const scriptId =
      slotType === "youtube"
        ? ytScript?.id ?? reelScript?.id ?? scriptIds[0]?.id ?? null
        : reelScript?.id ?? scriptIds[0]?.id ?? null;

    const res = await fetch("/api/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        script_id: scriptId,
        slot_date: slotDate,
        slot_type: slotType,
        pillar,
        status: "scripted",
        notes: title,
      }),
    });

    setSaving(false);
    if (!res.ok) {
      setError("Failed to schedule. Check console.");
      console.error("[send-to-calendar] failed", await res.text());
      return;
    }
    setOpen(false);
    router.push("/calendar");
  }

  void ideaId;
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Calendar /> Send to calendar
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Schedule this script</DialogTitle>
            <DialogDescription className="truncate">{title}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 pt-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs uppercase tracking-wide text-muted-foreground">
                Date
              </label>
              <Input
                type="date"
                value={slotDate}
                onChange={(e) => setSlotDate(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs uppercase tracking-wide text-muted-foreground">
                Slot
              </label>
              <Select
                value={slotType}
                onValueChange={(v) => v && setSlotType(v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reel_1">Reel 1</SelectItem>
                  <SelectItem value="reel_2">Reel 2</SelectItem>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="carousel">Carousel</SelectItem>
                  <SelectItem value="fb_post">FB Post</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Scheduling…" : "Schedule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
