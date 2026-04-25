"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  sourceTable: "creator_posts" | "learning_refs";
  sourceId: number;
  defaultTitle?: string | null;
  defaultHook?: string | null;
  size?: "xs" | "sm" | "default";
  variant?: "default" | "outline" | "ghost" | "secondary";
  label?: string;
  onCreated?: (projectId: number) => void;
};

export function CreateProjectButton({
  sourceTable,
  sourceId,
  defaultTitle,
  defaultHook,
  size = "xs",
  variant = "outline",
  label = "Create project",
  onCreated,
}: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const create = async () => {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/projects/from-source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_table: sourceTable,
          source_id: sourceId,
          title: defaultTitle ?? undefined,
          hook: defaultHook ?? undefined,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        setErr(json.error || `HTTP ${res.status}`);
        return;
      }
      onCreated?.(json.id);
      router.push(`/scripts/${json.id}`);
      router.refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <Button size={size} variant={variant} onClick={create} disabled={busy}>
        <Sparkles className="h-3 w-3 mr-1" />
        {busy ? "Creating…" : label}
      </Button>
      {err && <span className="text-[10px] text-red-400">{err}</span>}
    </div>
  );
}
