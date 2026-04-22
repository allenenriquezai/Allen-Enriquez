import { notFound } from "next/navigation";
import db from "@/lib/db";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScriptEditor } from "@/components/script-editor";
import { SendToCalendarButton } from "./send-to-calendar-button";

type IdeaRow = {
  id: number;
  title: string;
  pillar: string | null;
  lane: string | null;
  modeled_after: string | null;
  status: string;
};

type ScriptRow = {
  id: number;
  idea_id: number;
  variant: string;
  body: string;
  word_count: number | null;
};

const VARIANTS: { key: string; label: string }[] = [
  { key: "reel", label: "Reel" },
  { key: "youtube", label: "YouTube" },
  { key: "carousel", label: "Carousel" },
  { key: "caption_fb", label: "Caption-FB" },
  { key: "caption_ig", label: "Caption-IG" },
  { key: "caption_tiktok", label: "Caption-TikTok" },
  { key: "caption_yt", label: "Caption-YT" },
  { key: "caption_x", label: "Caption-X" },
];

export default async function ScriptDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ideaId = Number(id);
  if (!Number.isFinite(ideaId)) notFound();

  const idea = db
    .prepare(
      `SELECT id, title, pillar, lane, modeled_after, status FROM ideas WHERE id = ?`,
    )
    .get(ideaId) as IdeaRow | undefined;
  if (!idea) notFound();

  const scripts = db
    .prepare(`SELECT id, idea_id, variant, body, word_count FROM scripts WHERE idea_id = ?`)
    .all(ideaId) as ScriptRow[];

  const byVariant = new Map(scripts.map((s) => [s.variant, s]));
  const defaultTab =
    VARIANTS.find((v) => byVariant.has(v.key))?.key ?? "reel";

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold leading-tight">{idea.title}</h1>
          <div className="flex flex-wrap gap-1.5">
            {idea.pillar && <Badge variant="secondary">{idea.pillar}</Badge>}
            {idea.lane && <Badge variant="outline">{idea.lane}</Badge>}
            <Badge variant="outline">{idea.status}</Badge>
          </div>
          {idea.modeled_after && (
            <p className="text-xs italic text-muted-foreground pt-1">
              Modeled after: {idea.modeled_after}
            </p>
          )}
        </div>
        <SendToCalendarButton
          ideaId={idea.id}
          title={idea.title}
          pillar={idea.pillar}
          scriptIds={scripts.map((s) => ({ variant: s.variant, id: s.id }))}
        />
      </div>

      <Tabs defaultValue={defaultTab} className="w-full">
        <TabsList className="flex-wrap h-auto">
          {VARIANTS.map((v) => (
            <TabsTrigger key={v.key} value={v.key}>
              {v.label}
              {byVariant.has(v.key) ? null : (
                <span className="ml-1 text-[10px] text-muted-foreground">
                  ·new
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>
        {VARIANTS.map((v) => {
          const s = byVariant.get(v.key);
          return (
            <TabsContent key={v.key} value={v.key} className="pt-4">
              <ScriptEditor
                ideaId={idea.id}
                variant={v.key}
                scriptId={s?.id ?? null}
                initialBody={s?.body ?? ""}
                initialWordCount={s?.word_count ?? null}
              />
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
