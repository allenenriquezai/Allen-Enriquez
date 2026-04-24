export const dynamic = "force-dynamic";

import db from "@/lib/db";
import { InspirationClient } from "./inspiration-client";
import type { LearningRef } from "@/components/reference-card";

type CreatorPost = {
  id: number;
  post_id: string;
  creator: string;
  platform: string;
  url: string;
  title: string | null;
  description: string | null;
  thumbnail_url: string | null;
  posted_at: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration_sec: number | null;
  transcript: string | null;
  hook: string | null;
  topic: string | null;
  why_it_works: string | null;
  fetched_at: string;
};

export default function InspirationPage() {
  const autoRefreshEnabled = process.env.CREATOR_FEED_AUTO_REFRESH !== "false";
  const posts = db
    .prepare(
      `SELECT id, post_id, creator, platform, url, title, description,
              thumbnail_url, posted_at, view_count, like_count, comment_count,
              duration_sec, transcript, hook, topic, why_it_works, fetched_at
       FROM creator_posts
       ORDER BY COALESCE(posted_at, fetched_at) DESC
       LIMIT 100`,
    )
    .all() as CreatorPost[];

  const refs = db
    .prepare(
      `SELECT id, url, creator, platform, category, title, notes, saved_at
       FROM learning_refs
       ORDER BY saved_at DESC`,
    )
    .all() as LearningRef[];

  return <InspirationClient posts={posts} refs={refs} autoRefreshEnabled={autoRefreshEnabled} />;
}
