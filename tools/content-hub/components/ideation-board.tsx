"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Plus, Pin, PinOff, Trash2, Save, X, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export type IdeationNote = {
  id: number;
  title: string;
  body: string | null;
  tags: string | null;
  author: string | null;
  pinned: number;
  idea_id: number | null;
  created_at: string;
  updated_at: string;
};

export type IdeationTag = { id: number; name: string };

const AUTHORS = ["allen", "wife", "claude"] as const;

export function IdeationBoard({
  initialNotes,
  initialTags,
}: {
  initialNotes: IdeationNote[];
  initialTags: IdeationTag[];
}) {
  const [notes, setNotes] = React.useState<IdeationNote[]>(initialNotes);
  const [tags, setTags] = React.useState<IdeationTag[]>(initialTags);
  const [filter, setFilter] = React.useState<string>("all");
  const [composing, setComposing] = React.useState(false);
  const [addingTag, setAddingTag] = React.useState(false);
  const [newTagName, setNewTagName] = React.useState("");

  async function addTag() {
    const name = newTagName.trim().toLowerCase();
    if (!name) return;
    const res = await fetch("/api/ideation/tags", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const data = await res.json();
    if (data.tag) {
      setTags((prev) =>
        prev.find((t) => t.id === data.tag.id)
          ? prev
          : [...prev, data.tag].sort((a, b) => a.name.localeCompare(b.name)),
      );
    }
    setNewTagName("");
    setAddingTag(false);
  }

  async function deleteTag(t: IdeationTag) {
    if (!confirm(`Remove tag "${t.name}"? Notes keep their tag text.`)) return;
    await fetch(`/api/ideation/tags?id=${t.id}`, { method: "DELETE" });
    setTags((prev) => prev.filter((x) => x.id !== t.id));
    if (filter === t.name) setFilter("all");
  }

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
        <div className="flex items-center flex-wrap gap-1 ml-2">
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
          {tags.map((t) => (
            <span key={t.id} className="group relative inline-flex items-center">
              <button
                type="button"
                onClick={() => setFilter(t.name)}
                className={cn(
                  "px-2 py-1 text-xs rounded border pr-5",
                  filter === t.name ? "border-[color:var(--brand)] text-[color:var(--brand)]" : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {t.name}
              </button>
              <button
                type="button"
                onClick={() => deleteTag(t)}
                title={`Delete tag ${t.name}`}
                className="absolute right-0.5 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center justify-center text-muted-foreground hover:text-red-400"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {addingTag ? (
            <span className="inline-flex items-center gap-1">
              <input
                autoFocus
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onBlur={() => {
                  if (newTagName.trim()) addTag();
                  else setAddingTag(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") addTag();
                  if (e.key === "Escape") {
                    setNewTagName("");
                    setAddingTag(false);
                  }
                }}
                placeholder="new tag"
                className="w-24 px-2 py-1 text-xs rounded border border-[color:var(--brand)]/40 bg-transparent focus:outline-none focus:border-[color:var(--brand)]"
              />
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setAddingTag(true)}
              className="px-2 py-1 text-xs rounded border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/40 inline-flex items-center gap-1"
            >
              <Plus className="size-3" />
              tag
            </button>
          )}
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
          <PromoteToProjectButton note={note} />
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
          {note.idea_id && (
            <div className="text-[10px] text-[color:var(--brand)]">
              Linked to project #{note.idea_id}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function PromoteToProjectButton({ note }: { note: IdeationNote }) {
  const router = useRouter();
  const [busy, setBusy] = React.useState(false);

  if (note.idea_id) {
    return (
      <button
        type="button"
        title={`Open project #${note.idea_id}`}
        onClick={() => router.push(`/scripts/${note.idea_id}`)}
        className="text-[color:var(--brand)] hover:opacity-80"
      >
        <Sparkles className="size-3.5" />
      </button>
    );
  }

  const promote = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/projects/from-note", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_id: note.id }),
      });
      const json = await res.json();
      if (res.ok) {
        router.push(`/scripts/${json.id}`);
        router.refresh();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      title="Promote to project"
      onClick={promote}
      disabled={busy}
      className="text-muted-foreground hover:text-[color:var(--brand)]"
    >
      <Sparkles className="size-3.5" />
    </button>
  );
}
