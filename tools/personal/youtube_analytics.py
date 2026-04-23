#!/usr/bin/env python3
"""
YouTube Analytics — pulls last 50 videos from Allen's channel into youtube_stats table.

Usage:
    python3 tools/youtube_analytics.py
    python3 tools/youtube_analytics.py --limit 20
    python3 tools/youtube_analytics.py --dry-run
"""

import argparse
import os
import pickle
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "tools" / "content-hub" / "content_hub.db"
TOKEN_FILE = BASE_DIR / "projects" / "personal" / "token_personal_ai.pickle"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
CHANNEL_ID = "UCbxyZe-sodJxfgQzj1qoAcA"  # @allenenriquezz


def get_credentials():
    if not TOKEN_FILE.exists():
        print(f"ERROR: Token not found at {TOKEN_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)

    scopes = getattr(creds, "scopes", None) or []
    if YOUTUBE_SCOPE not in scopes:
        print(
            f"ERROR: Token missing YouTube scope.\n"
            f"Add '{YOUTUBE_SCOPE}' to SCOPES in tools/auth_personal.py, then re-run it.",
            file=sys.stderr,
        )
        sys.exit(1)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def fetch_videos(youtube, limit: int) -> list[dict]:
    # Get uploads playlist ID
    ch_res = youtube.channels().list(id=CHANNEL_ID, part="contentDetails").execute()
    items = ch_res.get("items", [])
    if not items:
        print("ERROR: Channel not found.", file=sys.stderr)
        sys.exit(1)

    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch video IDs from uploads playlist
    video_ids = []
    page_token = None
    while len(video_ids) < limit:
        batch = min(50, limit - len(video_ids))
        params = dict(playlistId=uploads_id, maxResults=batch, part="snippet,contentDetails")
        if page_token:
            params["pageToken"] = page_token
        pl_res = youtube.playlistItems().list(**params).execute()
        for item in pl_res.get("items", []):
            vid = item["contentDetails"].get("videoId")
            if vid:
                video_ids.append(vid)
        page_token = pl_res.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        return []

    # Batch fetch stats
    stats_res = (
        youtube.videos()
        .list(id=",".join(video_ids), part="statistics,snippet", maxResults=50)
        .execute()
    )

    videos = []
    for item in stats_res.get("items", []):
        vid_id = item["id"]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        videos.append(
            {
                "video_id": vid_id,
                "title": snippet.get("title"),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "published_at": snippet.get("publishedAt"),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return videos


def upsert_videos(videos: list[dict]) -> int:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS youtube_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL UNIQUE,
            title TEXT,
            url TEXT NOT NULL,
            published_at TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    added = 0
    for v in videos:
        cur.execute(
            """INSERT OR REPLACE INTO youtube_stats
               (video_id, title, url, published_at, views, likes, comments, fetched_at)
               VALUES (:video_id, :title, :url, :published_at, :views, :likes, :comments, :fetched_at)""",
            v,
        )
        added += 1
    conn.commit()
    conn.close()
    return added


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube video stats into content hub DB")
    parser.add_argument("--limit", type=int, default=50, help="Max videos to fetch (default 50)")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing to DB")
    args = parser.parse_args()

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    print(f"Fetching up to {args.limit} videos from your YouTube channel…")
    videos = fetch_videos(youtube, args.limit)
    print(f"Found {len(videos)} videos.")

    if args.dry_run:
        for v in videos:
            print(f"  [{v['published_at'][:10]}] {v['title']} — {v['views']}v {v['likes']}l {v['comments']}c")
        print("DRY RUN — nothing written.")
        return

    added = upsert_videos(videos)
    print(f"YOUTUBE_STATS_ADDED={added}")


if __name__ == "__main__":
    main()
