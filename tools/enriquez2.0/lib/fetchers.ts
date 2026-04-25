import Parser from "rss-parser";
import { Octokit } from "@octokit/rest";
import type { RawItem } from "./sources.js";

const rss = new Parser({ timeout: 15000 });

function hash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return Math.abs(h).toString(36);
}

export async function fetchRss(feedUrl: string, sinceMs: number): Promise<RawItem[]> {
  try {
    const feed = await rss.parseURL(feedUrl);
    const out: RawItem[] = [];
    for (const it of feed.items ?? []) {
      const pub = it.pubDate ? new Date(it.pubDate).getTime() : Date.now();
      if (pub < sinceMs) continue;
      const url = it.link ?? "";
      const title = (it.title ?? "").trim();
      if (!url || !title) continue;
      out.push({
        id: `rss:${hash(url)}`,
        source: `rss:${feed.title ?? feedUrl}`,
        title,
        url,
        content: (it.contentSnippet ?? it.content ?? "").slice(0, 2000),
        published_at: new Date(pub).toISOString(),
      });
    }
    return out;
  } catch (e) {
    console.error(`[rss] ${feedUrl}: ${(e as Error).message}`);
    return [];
  }
}

export async function fetchGithubReleases(repo: string, sinceMs: number): Promise<RawItem[]> {
  try {
    const [owner, name] = repo.split("/");
    const oct = new Octokit({ auth: process.env.GITHUB_TOKEN });
    const { data } = await oct.repos.listReleases({ owner, repo: name, per_page: 10 });
    const out: RawItem[] = [];
    for (const r of data) {
      const pub = r.published_at ? new Date(r.published_at).getTime() : 0;
      if (pub < sinceMs) continue;
      out.push({
        id: `gh:${repo}:${r.id}`,
        source: `github:${repo}`,
        title: `${repo} ${r.tag_name}: ${r.name ?? ""}`.trim(),
        url: r.html_url,
        content: (r.body ?? "").slice(0, 2000),
        published_at: new Date(pub).toISOString(),
      });
    }
    return out;
  } catch (e) {
    console.error(`[gh] ${repo}: ${(e as Error).message}`);
    return [];
  }
}

export async function fetchReddit(subreddit: string, sinceMs: number, hotThreshold: number): Promise<RawItem[]> {
  try {
    const url = `https://www.reddit.com/r/${subreddit}/top.json?t=week&limit=25`;
    const res = await fetch(url, { headers: { "User-Agent": "second-brain/0.1 (allen)" } });
    if (!res.ok) {
      console.error(`[reddit] r/${subreddit}: ${res.status}`);
      return [];
    }
    const data = (await res.json()) as { data: { children: Array<{ data: RedditPost }> } };
    const out: RawItem[] = [];
    for (const child of data.data?.children ?? []) {
      const p = child.data;
      const pub = p.created_utc * 1000;
      if (pub < sinceMs) continue;
      if (p.score < hotThreshold) continue;
      if (p.stickied || p.over_18) continue;
      out.push({
        id: `rd:${p.id}`,
        source: `reddit:r/${subreddit}`,
        title: p.title,
        url: `https://www.reddit.com${p.permalink}`,
        content: (p.selftext ?? "").slice(0, 2000),
        published_at: new Date(pub).toISOString(),
      });
    }
    return out;
  } catch (e) {
    console.error(`[reddit] r/${subreddit}: ${(e as Error).message}`);
    return [];
  }
}

interface RedditPost {
  id: string;
  title: string;
  selftext?: string;
  permalink: string;
  score: number;
  created_utc: number;
  stickied?: boolean;
  over_18?: boolean;
}
