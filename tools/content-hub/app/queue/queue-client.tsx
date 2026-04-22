"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Copy, Check } from "lucide-react";

export type Caption = { variant: string; body: string };

export type QueueSlot = {
  schedule_id: number;
  slot_date: string;
  slot_type: string;
  status: string;
  notes: string | null;
  idea_id: number | null;
  title: string | null;
  pillar: string | null;
  captions: Caption[];
};

const PLATFORM_TABS: { key: string; label: string }[] = [
  { key: "caption_ig", label: "IG / FB" },
  { key: "caption_tiktok", label: "TikTok" },
  { key: "caption_yt", label: "YT Shorts" },
  { key: "caption_x", label: "LinkedIn" },
];

const SLOT_LABELS: Record<string, string> = {
  reel_1: "Reel · Slot 1",
  reel_2: "Reel · Slot 2",
  carousel: "Carousel",
  youtube: "YouTube",
  fb_post: "FB Post",
};

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, React.CSSProperties> = {
    filmed: { color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.08)" },
    edited: { color: "var(--brand)", border: "1px solid rgba(2,179,233,0.3)", background: "rgba(2,179,233,0.08)" },
    planned: { color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.08)" },
    posted: { color: "var(--muted-foreground)", border: "1px solid rgba(128,128,128,0.2)", background: "rgba(128,128,128,0.06)" },
  };
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-[0.68rem] font-semibold uppercase tracking-wide"
      style={styles[status] ?? { border: "1px solid var(--border)" }}
    >
      {status}
    </span>
  );
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

export function QueueClient({ slots }: { slots: QueueSlot[] }) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (slots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No upcoming posts scheduled. Add slots in Calendar.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {slots.map((slot) => {
        const captionMap: Record<string, string> = {};
        for (const c of slot.captions) captionMap[c.variant] = c.body;
        const hasCaptions = slot.captions.length > 0;
        const availableTabs = PLATFORM_TABS.filter(t => captionMap[t.key]);

        return (
          <Card key={slot.schedule_id} className="overflow-hidden">
            <CardHeader className="pb-3 border-b border-border space-y-0">
              {/* Row 1: status + date + slot type */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={slot.status} />
                  <span
                    className="text-sm font-medium"
                    style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.04em" }}
                  >
                    {formatDate(slot.slot_date)}
                  </span>
                  {slot.notes && (
                    <span
                      className="text-xs"
                      style={{ color: "var(--brand)", fontFamily: "var(--font-roboto-mono)" }}
                    >
                      · {slot.notes}
                    </span>
                  )}
                </div>
                <span className="ae-mono-label opacity-60">
                  {SLOT_LABELS[slot.slot_type] ?? slot.slot_type}
                </span>
              </div>
              {/* Row 2: title + pillar */}
              {slot.title && (
                <div className="pt-2 flex items-center gap-2 flex-wrap">
                  <h2 className="text-base font-semibold leading-tight">{slot.title}</h2>
                  {slot.pillar && (
                    <Badge variant="outline" className="text-[0.68rem] px-1.5 py-0">
                      {slot.pillar.replace("_", " ")}
                    </Badge>
                  )}
                </div>
              )}
            </CardHeader>

            <CardContent className="pt-4 pb-5">
              {!hasCaptions ? (
                <p className="text-sm text-muted-foreground">No captions written yet.</p>
              ) : (
                <Tabs defaultValue={availableTabs[0]?.key ?? "caption_ig"}>
                  <TabsList className="mb-3 h-8">
                    {availableTabs.map(tab => (
                      <TabsTrigger key={tab.key} value={tab.key} className="text-xs px-3">
                        {tab.label}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {availableTabs.map(tab => {
                    const body = captionMap[tab.key];
                    const copyKey = `${slot.schedule_id}-${tab.key}`;
                    const copied = copiedKey === copyKey;
                    return (
                      <TabsContent key={tab.key} value={tab.key} className="mt-0">
                        <div className="relative group">
                          <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed p-4 pr-20 rounded-lg bg-muted/20 border border-border/40 min-h-[80px]">
                            {body}
                          </pre>
                          <Button
                            size="sm"
                            variant="outline"
                            className="absolute top-3 right-3 h-7 px-2.5 text-xs gap-1.5 opacity-70 hover:opacity-100 transition-opacity"
                            onClick={() => handleCopy(body, copyKey)}
                          >
                            {copied ? (
                              <>
                                <Check className="h-3 w-3" style={{ color: "#22c55e" }} />
                                <span style={{ color: "#22c55e" }}>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </Button>
                        </div>
                      </TabsContent>
                    );
                  })}
                </Tabs>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
