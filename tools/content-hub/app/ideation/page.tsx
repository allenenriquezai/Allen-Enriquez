export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { StudioSubNav } from "@/components/studio-sub-nav";
import { IdeationBoard } from "@/components/ideation-board";

export type IdeationNote = {
  id: number;
  title: string;
  body: string | null;
  tags: string | null;
  author: string | null;
  pinned: number;
  created_at: string;
  updated_at: string;
};

export default function IdeationPage() {
  const notes = db
    .prepare(
      "SELECT * FROM ideation_notes ORDER BY pinned DESC, updated_at DESC",
    )
    .all() as IdeationNote[];

  return (
    <div className="space-y-4">
      <StudioSubNav />
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Ideation</h1>
        <p className="text-sm text-muted-foreground">
          Free-form notes for Allen, wife & Claude. Psychology, editing, hooks, frameworks — anything that shapes how we make content.
        </p>
      </div>
      <IdeationBoard initialNotes={notes} />
    </div>
  );
}
