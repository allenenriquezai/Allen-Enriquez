import fs from "node:fs";
import path from "node:path";
import { SB_ROOT } from "../lib/env.js";
import {
  dbExists,
  openReadOnly,
  getSchedule,
  getPostsLast30d,
  getActiveIdeas,
  type PostRow,
} from "../lib/content-hub-db.js";

interface ContentHubState {
  generated_at: string;
  source_db: string;
  schedule_this_week: ReturnType<typeof getSchedule>;
  schedule_next_week: ReturnType<typeof getSchedule>;
  posts_last_30d: PostRow[];
  posts_summary: {
    total: number;
    by_platform: Record<string, number>;
    avg_views: number;
    top_5: Array<{ title: string | null; platform: string; views: number; url: string | null }>;
  };
  active_ideas: ReturnType<typeof getActiveIdeas>;
  cadence_check: {
    posts_this_week: number;
    posts_last_week: number;
    target_per_week: number;
    on_track: boolean;
  };
}

function isoDate(offsetDays: number): string {
  return new Date(Date.now() + offsetDays * 86400_000).toISOString().slice(0, 10);
}

function startOfWeek(): string {
  const d = new Date();
  const day = d.getUTCDay();
  d.setUTCDate(d.getUTCDate() - day);
  return d.toISOString().slice(0, 10);
}

function endOfWeek(): string {
  const d = new Date();
  const day = d.getUTCDay();
  d.setUTCDate(d.getUTCDate() - day + 6);
  return d.toISOString().slice(0, 10);
}

function summarizePosts(posts: PostRow[]) {
  const byPlatform: Record<string, number> = {};
  let totalViews = 0;
  for (const p of posts) {
    byPlatform[p.platform] = (byPlatform[p.platform] ?? 0) + 1;
    totalViews += p.views;
  }
  const top5 = [...posts]
    .sort((a, b) => b.views - a.views)
    .slice(0, 5)
    .map((p) => ({ title: p.asset_title, platform: p.platform, views: p.views, url: p.url }));
  return {
    total: posts.length,
    by_platform: byPlatform,
    avg_views: posts.length > 0 ? Math.round(totalViews / posts.length) : 0,
    top_5: top5,
  };
}

function cadenceCheck(posts: PostRow[]) {
  const now = Date.now();
  const oneWeekAgo = now - 7 * 86400_000;
  const twoWeeksAgo = now - 14 * 86400_000;
  let thisWeek = 0;
  let lastWeek = 0;
  for (const p of posts) {
    if (!p.posted_at) continue;
    const t = Date.parse(p.posted_at);
    if (t >= oneWeekAgo) thisWeek++;
    else if (t >= twoWeeksAgo) lastWeek++;
  }
  const target = 10; // 2 reels + 2 carousels + 1 long-form * ~2 platforms = ~10/wk per content_volume_target memory
  return { posts_this_week: thisWeek, posts_last_week: lastWeek, target_per_week: target, on_track: thisWeek >= target };
}

function main() {
  if (!dbExists()) {
    console.log("[content-hub] DB not found, skipping mirror");
    return;
  }
  const db = openReadOnly();
  try {
    const weekStart = startOfWeek();
    const weekEnd = endOfWeek();
    const nextWeekStart = isoDate(7 - new Date().getUTCDay());
    const nextWeekEnd = isoDate(13 - new Date().getUTCDay());

    const scheduleThisWeek = getSchedule(db, weekStart, weekEnd);
    const scheduleNextWeek = getSchedule(db, nextWeekStart, nextWeekEnd);
    const posts30d = getPostsLast30d(db);
    const ideas = getActiveIdeas(db);

    const state: ContentHubState = {
      generated_at: new Date().toISOString(),
      source_db: "tools/content-hub/content_hub.db",
      schedule_this_week: scheduleThisWeek,
      schedule_next_week: scheduleNextWeek,
      posts_last_30d: posts30d,
      posts_summary: summarizePosts(posts30d),
      active_ideas: ideas,
      cadence_check: cadenceCheck(posts30d),
    };

    fs.mkdirSync(path.join(SB_ROOT, "state"), { recursive: true });
    fs.writeFileSync(path.join(SB_ROOT, "state", "content-hub.json"), JSON.stringify(state, null, 2));

    const sched = scheduleThisWeek.length;
    const published = state.posts_summary.total;
    const onTrack = state.cadence_check.on_track ? "on track" : "BEHIND";
    console.log(
      `[content-hub] ${published} posts/30d (${state.posts_summary.avg_views} avg views), ${sched} slots this week, ${ideas.length} active projects — ${onTrack}`,
    );
  } finally {
    db.close();
  }
}

main();
