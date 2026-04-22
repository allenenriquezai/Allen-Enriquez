"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export interface InboxMessage {
  id: number;
  platform: string;
  thread_type: string;
  author: string | null;
  thread_text: string;
  reply_text: string | null;
  status: string;
  received_at: string;
}

export function InboxColumn({
  title,
  messages,
  onRefresh,
}: {
  title: string;
  messages: InboxMessage[];
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 min-w-0">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Badge variant="secondary">{messages.length}</Badge>
      </div>
      <div className="flex flex-col gap-2">
        {messages.length === 0 && (
          <div className="text-xs text-muted-foreground border border-dashed border-border rounded-lg p-4 text-center">
            No messages.
          </div>
        )}
        {messages.map((m) => (
          <MessageCard key={m.id} message={m} onRefresh={onRefresh} />
        ))}
      </div>
    </div>
  );
}

function MessageCard({
  message,
  onRefresh,
}: {
  message: InboxMessage;
  onRefresh: () => void;
}) {
  const [replying, setReplying] = useState(false);
  const [draft, setDraft] = useState(message.reply_text ?? "");

  const patch = async (body: Record<string, unknown>) => {
    await fetch(`/api/inbox/${message.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    onRefresh();
  };

  return (
    <div className="rounded-xl bg-card ring-1 ring-foreground/10 p-3 text-sm flex flex-col gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="outline">{message.platform}</Badge>
        <span className="text-xs text-muted-foreground truncate">
          {message.author ?? "anon"}
        </span>
        <span className="ml-auto">
          <StatusBadge status={message.status} />
        </span>
      </div>
      <p className="text-sm leading-snug line-clamp-3">{message.thread_text}</p>
      {message.reply_text && !replying && (
        <div className="text-xs text-muted-foreground border-l-2 border-primary/40 pl-2">
          <span className="text-primary">reply:</span> {message.reply_text}
        </div>
      )}
      {replying ? (
        <div className="flex flex-col gap-2">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write reply…"
            className="min-h-20 text-xs"
          />
          <div className="flex gap-1.5">
            <Button
              size="sm"
              onClick={async () => {
                await patch({ reply_text: draft, status: "replied" });
                setReplying(false);
              }}
            >
              Save
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setReplying(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex gap-1.5 flex-wrap">
          <Button size="xs" variant="outline" onClick={() => setReplying(true)}>
            Reply
          </Button>
          <Button
            size="xs"
            variant="ghost"
            onClick={() => patch({ status: "ignored" })}
          >
            Ignore
          </Button>
          <Button
            size="xs"
            variant="ghost"
            onClick={() => patch({ status: "escalated" })}
          >
            Escalate
          </Button>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "replied"
      ? "default"
      : status === "escalated"
        ? "destructive"
        : status === "ignored"
          ? "secondary"
          : "outline";
  return <Badge variant={variant}>{status}</Badge>;
}
