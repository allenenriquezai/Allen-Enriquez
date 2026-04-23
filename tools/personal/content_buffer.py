#!/usr/bin/env python3
"""
Content buffer tracker for Allen's personal brand.
Tracks raw recordings, scripts, and published content to calculate buffer depth.

Usage:
    python3 tools/content_buffer.py status           # Show buffer status
    python3 tools/content_buffer.py add-recording    # Log a new raw recording
    python3 tools/content_buffer.py add-script       # Log a new script ready
    python3 tools/content_buffer.py add-published    # Log published content
    python3 tools/content_buffer.py add-recording --title "AI automation for VAs" --type youtube --date 2026-04-11
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUFFER_FILE = PROJECT_ROOT / "projects" / "personal" / ".tmp" / "content-buffer.json"


def load_buffer():
    if BUFFER_FILE.exists():
        with open(BUFFER_FILE) as f:
            return json.load(f)
    return {
        "recordings": [],
        "scripts_ready": [],
        "published": [],
        "last_updated": datetime.now().isoformat()
    }


def save_buffer(data):
    BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    with open(BUFFER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def status(data):
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    recordings = data.get("recordings", [])
    scripts = data.get("scripts_ready", [])
    published = data.get("published", [])

    # Count unpublished recordings (raw footage waiting to be edited)
    unpublished_recordings = [r for r in recordings if not r.get("published", False)]

    # Count scripts that haven't been recorded yet
    unrecorded_scripts = [s for s in scripts if not s.get("recorded", False)]

    # Published this week
    published_this_week = [
        p for p in published
        if datetime.fromisoformat(p["date"]) >= week_ago
    ]

    # Calculate buffer (weeks ahead)
    # Assumption: Allen publishes ~5 pieces/week (1 YouTube + 4 reels/carousels)
    target_per_week = 5
    ready_pieces = len(unpublished_recordings) + len(unrecorded_scripts)
    buffer_weeks = round(ready_pieces / target_per_week, 1) if target_per_week > 0 else 0

    print(f"\n{'=' * 50}")
    print(f"  CONTENT BUFFER STATUS")
    print(f"{'=' * 50}")
    print(f"  Raw recordings waiting:  {len(unpublished_recordings)}")
    print(f"  Scripts ready:           {len(unrecorded_scripts)}")
    print(f"  Published this week:     {len(published_this_week)}")
    print(f"  Total published:         {len(published)}")
    print(f"  Buffer depth:            {buffer_weeks} weeks")
    print(f"{'=' * 50}")

    if buffer_weeks < 1:
        print(f"  *** BUFFER LOW — Block time to batch record! ***")
    elif buffer_weeks < 2:
        print(f"  Buffer OK but thin. Record more this week.")
    else:
        print(f"  Buffer healthy.")

    print()
    return {
        "recordings_waiting": len(unpublished_recordings),
        "scripts_ready": len(unrecorded_scripts),
        "published_this_week": len(published_this_week),
        "buffer_weeks": buffer_weeks,
    }


def add_item(data, category, title, content_type, date_str):
    if date_str:
        date = date_str
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    item = {
        "title": title,
        "type": content_type,
        "date": date,
        "added": datetime.now().isoformat(),
    }

    if category == "recordings":
        item["published"] = False
    elif category == "scripts_ready":
        item["recorded"] = False

    data.setdefault(category, []).append(item)
    save_buffer(data)
    print(f"  Added to {category}: {title} ({content_type}) — {date}")


def main():
    parser = argparse.ArgumentParser(description="Content buffer tracker")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show buffer status")

    for cmd in ["add-recording", "add-script", "add-published"]:
        p = sub.add_parser(cmd, help=f"Log a new {cmd.replace('add-', '')}")
        p.add_argument("--title", required=True, help="Content title")
        p.add_argument("--type", default="reel",
                       choices=["youtube", "reel", "carousel", "fb-post", "linkedin"],
                       help="Content type")
        p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")

    args = parser.parse_args()
    data = load_buffer()

    if args.command == "status":
        status(data)
    elif args.command == "add-recording":
        add_item(data, "recordings", args.title, args.type, args.date)
    elif args.command == "add-script":
        add_item(data, "scripts_ready", args.title, args.type, args.date)
    elif args.command == "add-published":
        add_item(data, "published", args.title, args.type, args.date)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
