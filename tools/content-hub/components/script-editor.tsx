"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export interface ScriptEditorProps {
  ideaId: number;
  variant: string;
  scriptId: number | null;
  initialBody: string;
  initialWordCount: number | null;
}

export function ScriptEditor({
  ideaId,
  variant,
  scriptId,
  initialBody,
  initialWordCount,
}: ScriptEditorProps) {
  const [body, setBody] = useState(initialBody);
  const [localId, setLocalId] = useState<number | null>(scriptId);
  const [wordCount, setWordCount] = useState<number | null>(initialWordCount);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      if (localId === null) {
        // Create row via POST /api/scripts
        const res = await fetch("/api/scripts", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ idea_id: ideaId, variant, body }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as { id: number };
        setLocalId(data.id);
      } else {
        const res = await fetch(`/api/scripts/${localId}`, {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ body }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as { word_count: number };
        setWordCount(data.word_count);
      }
      setSavedAt(new Date().toLocaleTimeString());
      startTransition(() => {});
    } finally {
      setSaving(false);
    }
  }

  const placeholder =
    localId === null
      ? `No ${variant} variant yet. Paste or write your script, then Save to generate.`
      : "";

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        className="min-h-64 font-mono text-sm"
      />
      <div className="flex items-center gap-3">
        <Button size="sm" onClick={save} disabled={saving || pending}>
          {saving ? "Saving…" : "Save"}
        </Button>
        <span className="text-xs text-muted-foreground">
          {wordCount !== null ? `${wordCount} words` : ""}
          {savedAt ? ` · saved ${savedAt}` : ""}
          {localId === null ? " · unsaved (new variant)" : ""}
        </span>
      </div>
    </div>
  );
}
