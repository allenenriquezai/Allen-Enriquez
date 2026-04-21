#!/usr/bin/env python3
"""
Creator Feed Watcher — daily fetch new posts from tracked creators (TikTok/YT).

Pulls metadata via yt-dlp, transcribes locally via whisper.cpp (free),
summarizes hook/topic/why-it-works via Claude Haiku (~$0.005/post),
stores in content_hub.db creator_posts table.

Config: projects/personal/creator_config.yaml
Output: tools/content-hub/content_hub.db (creator_posts table)

Usage:
    python3 tools/creator_feed.py                   # fetch all creators, process new posts
    python3 tools/creator_feed.py --creator Justyn  # single creator by name prefix
    python3 tools/creator_feed.py --limit 1         # 1 post per platform (testing)
    python3 tools/creator_feed.py --dry-run         # list what would be fetched, no DB write
    python3 tools/creator_feed.py --no-transcribe   # metadata only (skip audio download + whisper)
    python3 tools/creator_feed.py --no-breakdown    # skip Claude summary
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from curl_cffi import requests as cffi_requests

_IMPERSONATE_TARGET = ImpersonateTarget("chrome")

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "projects" / "personal" / "creator_config.yaml"
DB_FILE = BASE_DIR / "tools" / "content-hub" / "content_hub.db"
PERSONAL_ENV = BASE_DIR / "projects" / "personal" / ".env"
TRANSCRIBE_SCRIPT = BASE_DIR / "tools" / "transcribe_video.py"


def load_env():
    if PERSONAL_ENV.exists():
        for line in PERSONAL_ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def db_connect():
    return sqlite3.connect(DB_FILE)


def seen_post_ids(conn, creator):
    rows = conn.execute(
        "SELECT post_id FROM creator_posts WHERE creator = ?", (creator,)
    ).fetchall()
    return {r[0] for r in rows}


_SECUID_CACHE = {}


def resolve_tiktok_feed(profile_url):
    """TikTok's yt-dlp user extractor is broken. Scrape profile HTML for
    secUid, return yt-dlp-compatible 'tiktokuser:<secUid>' URL."""
    if profile_url in _SECUID_CACHE:
        return _SECUID_CACHE[profile_url]
    try:
        r = cffi_requests.get(profile_url, impersonate="chrome", timeout=30)
        m = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
            r.text,
            re.DOTALL,
        )
        if not m:
            return None
        data = json.loads(m.group(1))
        sec_uid = (
            data.get("__DEFAULT_SCOPE__", {})
            .get("webapp.user-detail", {})
            .get("userInfo", {})
            .get("user", {})
            .get("secUid")
        )
        if not sec_uid:
            return None
        feed_url = f"tiktokuser:{sec_uid}"
        _SECUID_CACHE[profile_url] = feed_url
        return feed_url
    except Exception as e:
        print(f"    ERROR secUid {profile_url}: {e}", file=sys.stderr)
        return None


def list_recent_posts(platform, platform_url, limit):
    """Use yt-dlp to list recent posts. Metadata only.
    TikTok profile URLs need a secUid lookup first."""
    feed_url = platform_url
    if platform == "tiktok" and "/@" in platform_url:
        resolved = resolve_tiktok_feed(platform_url)
        if not resolved:
            print(
                f"    ERROR: could not resolve secUid for {platform_url}",
                file=sys.stderr,
            )
            return []
        feed_url = resolved

    ydl_opts = {
        **_YT_COMMON,
        "extract_flat": True,
        "playlistend": limit,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(feed_url, download=False)
        except Exception as e:
            print(f"    ERROR list {feed_url}: {e}", file=sys.stderr)
            return []
    entries = info.get("entries") or []
    return entries[:limit]


_YT_COMMON = {
    "quiet": True,
    "impersonate": _IMPERSONATE_TARGET,  # needs curl_cffi; TikTok blocks non-browser fingerprints
    "extractor_retries": 3,
}


def fetch_post_detail(post_url):
    """Full metadata for a single post (no download)."""
    ydl_opts = {**_YT_COMMON, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            return ydl.extract_info(post_url, download=False)
        except Exception as e:
            print(f"    ERROR detail {post_url}: {e}", file=sys.stderr)
            return None


def download_audio(post_url, out_dir):
    """Download audio (or full video — transcribe_video.py extracts audio via ffmpeg)
    for whisper. Returns path or None."""
    out_tmpl = str(out_dir / "audio.%(ext)s")
    ydl_opts = {
        **_YT_COMMON,
        # TikTok only serves combined mp4 — fall through to "best"
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([post_url])
        except Exception as e:
            print(f"    ERROR audio {post_url}: {e}", file=sys.stderr)
            return None
    for f in out_dir.iterdir():
        if f.name.startswith("audio."):
            return f
    return None


def transcribe(audio_path, out_dir):
    """Call tools/transcribe_video.py → returns transcript text or empty string."""
    prefix = str(out_dir / "whisper")
    try:
        subprocess.run(
            [
                "python3",
                str(TRANSCRIBE_SCRIPT),
                str(audio_path),
                "--out",
                prefix,
            ],
            check=True,
            capture_output=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        print(f"    ERROR transcribe: {e.stderr.decode()[-300:]}", file=sys.stderr)
        return ""
    except subprocess.TimeoutExpired:
        print(f"    ERROR transcribe timeout", file=sys.stderr)
        return ""
    txt = Path(prefix + ".txt")
    return txt.read_text() if txt.exists() else ""


BREAKDOWN_PROMPT = """You are analyzing a short-form video post from an AI/content creator.

CREATOR: {creator}
TITLE: {title}
DESCRIPTION: {description}
TRANSCRIPT:
{transcript}

Return STRICT JSON (no markdown, no prose outside JSON):
{{
  "hook": "<first 1-2 sentences verbatim from transcript or title — the attention grabber>",
  "topic": "<1 sentence — what this post is actually about>",
  "why_it_works": "<1-2 sentences — what pattern/angle makes this post work. Be specific: pattern-interrupt, bold claim, number hook, contrarian, etc.>"
}}
"""


def call_claude(prompt, max_tokens=600):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-key-here":
        return None
    body = json.dumps(
        {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        return resp["content"][0]["text"]
    except Exception as e:
        print(f"    Claude error: {e}", file=sys.stderr)
        return None


def parse_breakdown(text):
    if not text:
        return {"hook": None, "topic": None, "why_it_works": None}
    # Strip code fences if model added them
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
        t = t.strip()
    try:
        data = json.loads(t)
        return {
            "hook": data.get("hook"),
            "topic": data.get("topic"),
            "why_it_works": data.get("why_it_works"),
        }
    except json.JSONDecodeError:
        return {"hook": None, "topic": None, "why_it_works": None}


def to_iso(ts):
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts)).isoformat()
    except Exception:
        return None


def process_post(entry, creator, platform, args, conn, handle=None):
    """entry = flat list entry from yt-dlp (may lack full metadata)."""
    post_id = entry.get("id") or entry.get("url")
    post_url = entry.get("webpage_url") or entry.get("url")
    if not post_id:
        return False

    # For TikTok, ALWAYS rebuild URL from handle — yt-dlp flat entries from
    # tiktokuser:secUid return URLs with the secUid in place of the handle,
    # which TikTok's web frontend rejects.
    if platform == "tiktok" and handle:
        post_url = f"https://www.tiktok.com/@{handle}/video/{post_id}"
    elif not post_url or not str(post_url).startswith("http"):
        if platform == "youtube":
            post_url = f"https://www.youtube.com/watch?v={post_id}"
        else:
            return False

    title = entry.get("title") or ""
    print(f"  [{platform}] {title[:60]}")

    if args.dry_run:
        return False

    detail = fetch_post_detail(post_url) or entry
    duration = detail.get("duration")

    transcript = ""
    if not args.no_transcribe and duration and duration <= args.max_duration:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            audio = download_audio(post_url, tdp)
            if audio:
                transcript = transcribe(audio, tdp)

    breakdown = {"hook": None, "topic": None, "why_it_works": None}
    if not args.no_breakdown and (transcript or title):
        prompt = BREAKDOWN_PROMPT.format(
            creator=creator,
            title=title,
            description=(detail.get("description") or "")[:500],
            transcript=(transcript or "[no transcript]")[:4000],
        )
        raw = call_claude(prompt)
        breakdown = parse_breakdown(raw)

    thumbnails = detail.get("thumbnails") or []
    thumbnail_url = thumbnails[-1]["url"] if thumbnails else detail.get("thumbnail")

    conn.execute(
        """
        INSERT OR IGNORE INTO creator_posts
        (post_id, creator, platform, url, title, description, thumbnail_url,
         posted_at, view_count, like_count, comment_count, duration_sec,
         transcript, hook, topic, why_it_works, raw_meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            post_id,
            creator,
            platform,
            post_url,
            title,
            (detail.get("description") or "")[:2000],
            thumbnail_url,
            to_iso(detail.get("timestamp")),
            detail.get("view_count"),
            detail.get("like_count"),
            detail.get("comment_count"),
            duration,
            transcript[:20000] if transcript else None,
            breakdown["hook"],
            breakdown["topic"],
            breakdown["why_it_works"],
            json.dumps({k: detail.get(k) for k in ["id", "title", "uploader", "upload_date", "channel_url"]}),
        ),
    )
    conn.commit()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--creator", help="Filter by creator name prefix")
    parser.add_argument("--limit", type=int, default=None, help="Override max_posts_per_run")
    parser.add_argument("--dry-run", action="store_true", help="List only, no DB writes")
    parser.add_argument("--no-transcribe", action="store_true")
    parser.add_argument("--no-breakdown", action="store_true")
    parser.add_argument("--max-duration", type=int, default=600)
    args = parser.parse_args()

    load_env()
    cfg = load_config()
    if args.limit is None:
        args.limit = cfg.get("max_posts_per_run", 5)

    conn = db_connect()
    added = 0
    skipped = 0

    for creator_cfg in cfg.get("creators", []):
        name = creator_cfg["name"]
        if args.creator and not name.lower().startswith(args.creator.lower()):
            continue
        print(f"\n=== {name} ===")
        seen = seen_post_ids(conn, name)

        for platform, url in creator_cfg.get("platforms", {}).items():
            print(f" [{platform}] {url}")
            handle = None
            if "/@" in url:
                handle = url.split("/@", 1)[1].split("/")[0].split("?")[0]
            posts = list_recent_posts(platform, url, args.limit)
            print(f"   found {len(posts)} recent posts")
            for entry in posts:
                pid = entry.get("id") or entry.get("url")
                if pid in seen:
                    skipped += 1
                    continue
                if process_post(entry, name, platform, args, conn, handle=handle):
                    added += 1

    conn.close()
    print(f"\nAdded {added} new posts ({skipped} already seen)")
    # machine-readable for /brief
    print(f"CREATOR_FEED_ADDED={added}")


if __name__ == "__main__":
    main()
