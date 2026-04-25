"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export interface PostOption {
  id: number;
  platform: string;
  asset_title: string | null;
  asset_type: string | null;
}

function FormRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

export function AddMetricsDialog({ posts, onSaved }: { posts: PostOption[]; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [postId, setPostId] = useState<string>("");
  const [form, setForm] = useState({
    views: 0,
    likes: 0,
    comments: 0,
    shares: 0,
    saves: 0,
    follows_gained: 0,
    recorded_at: new Date().toISOString().slice(0, 10),
  });

  const save = async () => {
    if (!postId) return;
    await fetch("/api/metrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: Number(postId), ...form }),
    });
    setOpen(false);
    setPostId("");
    onSaved();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>Add metrics</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add metrics</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Post</label>
            {posts.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No posts yet. Create an asset + post first (Library tab).
              </p>
            ) : (
              <select
                value={postId}
                onChange={(e) => setPostId(e.target.value)}
                className="h-8 rounded-lg bg-transparent border border-input px-2 text-sm"
              >
                <option value="">Select a post…</option>
                {posts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {(p.asset_title ?? `#${p.id}`) + " — " + p.platform}
                  </option>
                ))}
              </select>
            )}
          </div>
          <FormRow label="Views">
            <Input type="number" value={form.views} onChange={(e) => setForm({ ...form, views: Number(e.target.value) })} />
          </FormRow>
          <div className="grid grid-cols-2 gap-2">
            <FormRow label="Likes">
              <Input type="number" value={form.likes} onChange={(e) => setForm({ ...form, likes: Number(e.target.value) })} />
            </FormRow>
            <FormRow label="Comments">
              <Input type="number" value={form.comments} onChange={(e) => setForm({ ...form, comments: Number(e.target.value) })} />
            </FormRow>
            <FormRow label="Shares">
              <Input type="number" value={form.shares} onChange={(e) => setForm({ ...form, shares: Number(e.target.value) })} />
            </FormRow>
            <FormRow label="Saves">
              <Input type="number" value={form.saves} onChange={(e) => setForm({ ...form, saves: Number(e.target.value) })} />
            </FormRow>
          </div>
          <FormRow label="Follows gained">
            <Input type="number" value={form.follows_gained} onChange={(e) => setForm({ ...form, follows_gained: Number(e.target.value) })} />
          </FormRow>
          <FormRow label="Recorded at">
            <Input type="date" value={form.recorded_at} onChange={(e) => setForm({ ...form, recorded_at: e.target.value })} />
          </FormRow>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={save} disabled={!postId}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
