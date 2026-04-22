"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bookmark, Check, ExternalLink, X } from "lucide-react";

export interface IdeaCardData {
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
  preview?: string | null;
}

export function IdeaCard({ idea }: { idea: IdeaCardData }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [localStatus, setLocalStatus] = useState(idea.status);

  async function act(action: "pick" | "skip" | "bookmark") {
    const res = await fetch("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ id: idea.id, action }),
    });
    if (!res.ok) return;
    const data = (await res.json()) as { status: string };
    setLocalStatus(data.status);
    if (action === "pick") {
      startTransition(() => router.push(`/scripts/${idea.id}`));
    } else {
      startTransition(() => router.refresh());
    }
  }

  const preview =
    (idea.preview ?? "").slice(0, 140) +
    ((idea.preview ?? "").length > 140 ? "…" : "");

  return (
    <Card className="flex flex-col gap-3">
      <CardHeader className="pb-0">
        <CardTitle className="text-base font-semibold leading-snug">
          <Link
            href={`/scripts/${idea.id}`}
            className="hover:text-primary transition-colors"
          >
            {idea.title}
          </Link>
        </CardTitle>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {idea.pillar && <Badge variant="secondary">{idea.pillar}</Badge>}
          {idea.lane && <Badge variant="outline">{idea.lane}</Badge>}
          {idea.day_of_week && (
            <Badge variant="outline">
              {idea.day_of_week}
              {idea.slot ? ` · ${idea.slot}` : ""}
            </Badge>
          )}
          <Badge
            variant={
              localStatus === "picked"
                ? "default"
                : localStatus === "bookmarked"
                  ? "secondary"
                  : localStatus === "dismissed"
                    ? "destructive"
                    : "outline"
            }
          >
            {localStatus}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {idea.modeled_after && (
          <p className="text-xs italic text-muted-foreground">
            Modeled after: {idea.modeled_after}
          </p>
        )}
        {preview && (
          <p className="text-sm text-foreground/80 line-clamp-3">{preview}</p>
        )}
        <div className="flex gap-1.5 pt-1 flex-wrap">
          <Button
            size="sm"
            variant="default"
            onClick={() => act("pick")}
            disabled={pending}
          >
            <Check /> Pick
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => act("bookmark")}
            disabled={pending}
          >
            <Bookmark /> Bookmark
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => act("skip")}
            disabled={pending}
          >
            <X /> Skip
          </Button>
          <Link href={`/scripts/${idea.id}`} className="ml-auto">
            <Button size="sm" variant="ghost" title="Open script">
              <ExternalLink />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
