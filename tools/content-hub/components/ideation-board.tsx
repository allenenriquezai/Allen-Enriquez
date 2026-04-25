"use client";

import * as React from "react";
import { Plus, Pin, PinOff, Trash2, Save } from "lucide-react";
import { cn } from "@/lib/utils";

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

const AUTHORS = ["allen", "wife", "claude"] as const;
const TAG_PRESETS = ["psychology", "editing", "hooks", "frameworks", "tooling", "ops"];

export function IdeationBoard({ initialNotes }: { initialNotes: IdeationNote[] }) {
  const [notes, setNotes] = React.useState<IdeationNote[]>(initialNotes);
  const [filter, setFilter] = React.useState<string>("all");
  const [composing, setComposing] = React.useState(false);

  const visible = notes.filter((n) => {
    if (filter === "all") return true;
    return (n.tags ?? "").split(",").map((s) => s.trim()).includes(filter);
  });

  async function addNote(payload: { title: string; body: string; tags: string; author: string }) {
    const res = await fetch("/api/ideation", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.note) setNotes((prev) => [data.note, ...prev]);
  }

  async function patchNote(id: number, patch: Partial<IdeationNote>) {
    const res = await fetch(`/api/ideation/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(patch),
    });
    const data = await res.json();
    if (data.note) {
      setNotes((prev) => prev.map((n) => (n.id === id ? data.note : n)));
    }
  }

  async function deleteNote(id: number) {
    if (!confirm("Delete this note?")) return;
    await fetch(`/api/ideation/${id}`, { method: "DELETE" });
    setNotes((prev) => prev.filter((n) => n.id !== id));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setComposing(true)}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold"
          style={{ background: "var(--brand)", color: "#000" }}
        >
          <Plus className="size-4" /> New note
        </button>
        <div className="flex items-center gap-1 ml-2">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded border",
              filter === "all" ? "border-[color:var(--brand)] text-[color:var(--brand)]" : "border-transparent text-muted-foreground",
            )}
          >
            All
          </button>
          {TAG_PRESETS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilter(t)}
              className={cn(
                "px-2 py-1 text-xs rounded border",
                filter === t ? "border-[color:var(--brand)] text-[color:var(--brand)]" : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {composing && (
        <NoteComposer
          onCancel={() => setComposing(false)}
          onSave={async (payload) => {
            await addNote(payload);
            setComposing(false);
          }}
        />
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {visible.length === 0 && (
          <div className="col-span-full text-sm text-muted-foreground">
            No notes yet. Click <em>New note</em> to capture an idea.
          </div>
        )}
        {visible.map((n) => (
          <NoteCard
            key={n.id}
            note={n}
            onPatch={(p) => patchNote(n.id, p)}
            onDelete={() => deleteNote(n.id)}
          />
        ))}
      </div>
    </div>
  );
}

function NoteComposer({
  onCancel,
  onSave,
}: {
  onCancel: () => void;
  onSave: (p: { title: string; body: string; tags: string; author: string }) => Promise<void>;
}) {
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [tags, setTags] = React.useState("");
  const [author, setAuthor] = React.useState<string>("allen");
  const [saving, setSaving] = React.useState(false);

  async function save() {
    if (!title.trim()) return;
    setSaving(true);
    await onSave({ title: title.trim(), body, tags, author });
    setSaving(false);
  }

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <input
        type="text"
        placeholder="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full bg-transparent text-lg font-semibold focus:outline-none"
        autoFocus
      />
      <textarea
        placeholder="Body — markdown welcome"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={5}
        className="w-full bg-transparent text-sm focus:outline-none resize-y"
      />
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className="rounded border bg-transparent px-2 py-1 text-xs"
        >
          {AUTHORS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="tags (comma)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="flex-1 rounded border bg-transparent px-2 py-1 text-xs"
        />
        <button
          type="button"
          onClick={save}
          disabled={saving || !title.trim()}
          className="flex items-center gap-1 rounded-md px-3 py-1 text-xs font-semibold disabled:opacity-60"
          style={{ background: "var(--brand)", color: "#000" }}
        >
          <Save className="size-3.5" />
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border px-3 py-1 text-xs"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function NoteCard({
  note,
  onPatch,
  onDelete,
}: {
  note: IdeationNote;
  onPatch: (p: Partial<IdeationNote>) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [editing, setEditing] = React.useState(false);
  const [title, setTitle] = React.useState(note.title);
  const [body, setBody] = React.useState(note.body ?? "");
  const [tags, setTags] = React.useState(note.tags ?? "");
  const tagList = (note.tags ?? "").split(",").map((s) => s.trim()).filter(Boolean);

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-3 space-y-2 text-sm",
        note.pinned ? "border-[color:var(--brand)]" : "border-sidebar-border",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        {editing ? (
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="flex-1 bg-transparent font-semibold focus:outline-none"
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-left font-semibold hover:underline"
          >
            {note.title}
          </button>
        )}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            title={note.pinned ? "Unpin" : "Pin"}
            onClick={() => onPatch({ pinned: note.pinned ? 0 : 1 })}
            className="text-muted-foreground hover:text-foreground"
          >
            {note.pinned ? <Pin className="size-3.5" /> : <PinOff className="size-3.5" />}
          </button>
          <button
            type="button"
            title="Delete"
            onClick={onDelete}
            className="text-muted-foreground hover:text-red-400"
          >
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>

      {editing ? (
        <>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            className="w-full bg-transparent text-xs focus:outline-none resize-y"
          />
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="tags (comma)"
            className="w-full rounded border bg-transparent px-2 py-1 text-xs"
          />
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setTitle(note.title);
                setBody(note.body ?? "");
                setTags(note.tags ?? "");
                setEditing(false);
              }}
              className="rounded-md border px-2 py-1 text-xs"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={async () => {
                await onPatch({ title, body, tags });
                setEditing(false);
              }}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold"
              style={{ background: "var(--brand)", color: "#000" }}
            >
              <Save className="size-3" /> Save
            </button>
          </div>
        </>
      ) : (
        <>
          {note.body && (
            <p className="whitespace-pre-wrap text-xs text-muted-foreground">
              {note.body}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-1.5">
            {tagList.map((t) => (
              <span
                key={t}
                className="rounded border border-[color:var(--brand)]/40 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-[color:var(--brand)]"
              >
                {t}
              </span>
            ))}
            <span className="ml-auto text-[10px] text-muted-foreground">
              {note.author ?? "—"} · {new Date(note.updated_at).toLocaleDateString()}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
