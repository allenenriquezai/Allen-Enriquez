#!/usr/bin/env python3
"""
Track the 30-day content campaign production status.

Usage:
    python3 tools/content_tracker.py init --days 30 --start 2026-04-10
    python3 tools/content_tracker.py status
    python3 tools/content_tracker.py today
    python3 tools/content_tracker.py mark --day 3 --type reel --slot 1 --status filmed
    python3 tools/content_tracker.py mark --day 3 --type youtube --status posted
    python3 tools/content_tracker.py report

Data: projects/personal/.tmp/content_tracker.json
"""

import argparse
import json
import os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA_FILE = os.path.join(ROOT, "projects", "personal", ".tmp", "content_tracker.json")


def load():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


def save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)


def init_campaign(days, start_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    campaign = {
        "campaign": "30-day-hormozi",
        "start_date": start_date,
        "total_days": days,
        "created": datetime.now().isoformat(),
        "days": [],
    }
    for i in range(days):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        day_entry = {
            "day": i + 1,
            "date": date,
            "reel_1": {"topic": "", "script": "pending", "filmed": "pending", "posted": "pending"},
            "reel_2": {"topic": "", "script": "pending", "filmed": "pending", "posted": "pending"},
            "youtube": {"topic": "", "script": "pending", "filmed": "pending", "posted": "pending"},
            "fb_posts": [],
        }
        campaign["days"].append(day_entry)
    save(campaign)
    print(f"Initialized {days}-day campaign starting {start_date}")
    print(f"Data: {DATA_FILE}")


def get_today_index(data):
    today = datetime.now().strftime("%Y-%m-%d")
    for d in data["days"]:
        if d["date"] == today:
            return d
    return None


def show_status(data):
    total = data["total_days"]
    scripted = 0
    filmed = 0
    posted = 0
    total_pieces = total * 3  # 2 reels + 1 youtube per day

    for d in data["days"]:
        for key in ["reel_1", "reel_2", "youtube"]:
            if d[key]["script"] not in ("pending", ""):
                scripted += 1
            if d[key]["filmed"] not in ("pending", ""):
                filmed += 1
            if d[key]["posted"] not in ("pending", ""):
                posted += 1

    today = get_today_index(data)
    today_label = f"Day {today['day']} ({today['date']})" if today else "No campaign day today"

    print(f"Campaign: {data['campaign']}")
    print(f"Today: {today_label}")
    print(f"Progress: {posted}/{total_pieces} posted | {filmed}/{total_pieces} filmed | {scripted}/{total_pieces} scripted")
    print(f"Days remaining: {total - (posted // 3)}")


def show_today(data):
    today = get_today_index(data)
    if not today:
        print("No campaign day today.")
        return

    print(f"=== Day {today['day']} ({today['date']}) ===\n")
    for key, label in [("reel_1", "Reel #1"), ("reel_2", "Reel #2"), ("youtube", "YouTube")]:
        item = today[key]
        topic = item["topic"] or "(no topic set)"
        status_parts = []
        for s in ["script", "filmed", "posted"]:
            val = item[s]
            icon = "x" if val in ("pending", "") else "v"
            status_parts.append(f"[{icon}] {s}: {val}")
        print(f"{label}: {topic}")
        print(f"  {' | '.join(status_parts)}")

    if today["fb_posts"]:
        print(f"\nFB posts: {len(today['fb_posts'])}")
        for fb in today["fb_posts"]:
            print(f"  - {fb.get('group', '?')}: {fb.get('status', 'pending')}")
    print()


def mark(data, day_num, content_type, slot, status):
    if day_num < 1 or day_num > len(data["days"]):
        print(f"Error: day {day_num} out of range (1-{len(data['days'])})")
        return

    day = data["days"][day_num - 1]

    if content_type == "reel":
        key = f"reel_{slot}"
        if key not in day:
            print(f"Error: slot {slot} invalid (use 1 or 2)")
            return
    elif content_type == "youtube":
        key = "youtube"
    elif content_type == "fb":
        day["fb_posts"].append({"status": status, "marked": datetime.now().isoformat()})
        save(data)
        print(f"Day {day_num}: FB post marked as {status}")
        return
    else:
        print(f"Error: unknown type '{content_type}' (use reel, youtube, fb)")
        return

    # Determine which field to update based on status value
    if status in ("scripted", "approved", "draft"):
        day[key]["script"] = status
    elif status == "filmed":
        day[key]["filmed"] = status
    elif status == "posted":
        day[key]["posted"] = status
    else:
        # Generic: set all to this status
        day[key]["script"] = status

    save(data)
    print(f"Day {day_num} {key}: marked as {status}")


def set_topic(data, day_num, content_type, slot, topic):
    if day_num < 1 or day_num > len(data["days"]):
        print(f"Error: day {day_num} out of range")
        return
    day = data["days"][day_num - 1]
    if content_type == "reel":
        key = f"reel_{slot}"
    else:
        key = "youtube"
    day[key]["topic"] = topic
    save(data)
    print(f"Day {day_num} {key}: topic set to '{topic}'")


def report(data):
    print(f"=== {data['campaign']} — Full Report ===\n")
    for d in data["days"]:
        pieces = []
        for key in ["reel_1", "reel_2", "youtube"]:
            item = d[key]
            if item["posted"] not in ("pending", ""):
                pieces.append("POSTED")
            elif item["filmed"] not in ("pending", ""):
                pieces.append("FILMED")
            elif item["script"] not in ("pending", ""):
                pieces.append("SCRIPTED")
            else:
                pieces.append("---")
        fb_count = len([fb for fb in d["fb_posts"] if fb.get("status") == "posted"])
        fb_str = f" +{fb_count}fb" if fb_count else ""
        print(f"Day {d['day']:2d} ({d['date']}): R1={pieces[0]:8s} R2={pieces[1]:8s} YT={pieces[2]:8s}{fb_str}")


def main():
    parser = argparse.ArgumentParser(description="Content campaign tracker")
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init")
    init_p.add_argument("--days", type=int, default=30)
    init_p.add_argument("--start", type=str, required=True)

    sub.add_parser("status")
    sub.add_parser("today")
    sub.add_parser("report")

    mark_p = sub.add_parser("mark")
    mark_p.add_argument("--day", type=int, required=True)
    mark_p.add_argument("--type", type=str, required=True, choices=["reel", "youtube", "fb"])
    mark_p.add_argument("--slot", type=int, default=1)
    mark_p.add_argument("--status", type=str, required=True)

    topic_p = sub.add_parser("topic")
    topic_p.add_argument("--day", type=int, required=True)
    topic_p.add_argument("--type", type=str, required=True, choices=["reel", "youtube"])
    topic_p.add_argument("--slot", type=int, default=1)
    topic_p.add_argument("--text", type=str, required=True)

    args = parser.parse_args()

    if args.command == "init":
        init_campaign(args.days, args.start)
    elif args.command in ("status", "today", "report", "mark", "topic"):
        data = load()
        if not data:
            print(f"No campaign found. Run: python3 tools/content_tracker.py init --days 30 --start YYYY-MM-DD")
            return
        if args.command == "status":
            show_status(data)
        elif args.command == "today":
            show_today(data)
        elif args.command == "report":
            report(data)
        elif args.command == "mark":
            mark(data, args.day, args.type, args.slot, args.status)
        elif args.command == "topic":
            set_topic(data, args.day, args.type, args.slot, args.text)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
