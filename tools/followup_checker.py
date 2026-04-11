#!/usr/bin/env python3
"""
Follow-up checker for Allen's personal brand outreach.
Reads outreach_log.jsonl and flags conversations that need follow-up.

Usage:
    python3 tools/followup_checker.py              # Show pending follow-ups
    python3 tools/followup_checker.py --json        # Output as JSON
    python3 tools/followup_checker.py --overdue     # Only show overdue (48h+ no reply)
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "projects" / "personal" / ".tmp" / "outreach_log.jsonl"


def load_log():
    entries = []
    if not LOG_FILE.exists():
        return entries
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def check_followups(entries, overdue_only=False):
    now = datetime.now()
    results = {
        "needs_reply": [],      # prospect replied, Allen hasn't responded
        "overdue_48h": [],      # sent touch, no reply after 48h
        "overdue_5d": [],       # sent touch 2, no reply after 5d
        "ready_touch_2": [],    # touch 1 sent, 48h passed, time for touch 2
        "ready_touch_3": [],    # touch 2 sent, 5d passed, time for touch 3
    }

    for entry in entries:
        status = entry.get("status", "").lower()
        name = entry.get("name", "Unknown")
        touch = entry.get("touch", 1)
        date_str = entry.get("date", "")
        channel = entry.get("channel", "")

        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        age = now - entry_date

        # Prospect replied — Allen needs to respond
        if status in ["replied", "responded"]:
            results["needs_reply"].append({
                "name": name,
                "channel": channel,
                "date": date_str,
                "age_hours": round(age.total_seconds() / 3600, 1),
                "priority": "HIGH" if age.total_seconds() < 1800 else "MEDIUM",
            })
            continue

        # Drafted or sent — check if follow-up is due
        if status in ["drafted", "sent"]:
            if touch == 1 and age > timedelta(hours=48):
                results["ready_touch_2"].append({
                    "name": name,
                    "channel": channel,
                    "date": date_str,
                    "days_since": age.days,
                })
            elif touch == 2 and age > timedelta(days=5):
                results["ready_touch_3"].append({
                    "name": name,
                    "channel": channel,
                    "date": date_str,
                    "days_since": age.days,
                })

    return results


def print_status(results):
    total_actions = (
        len(results["needs_reply"]) +
        len(results["ready_touch_2"]) +
        len(results["ready_touch_3"])
    )

    print(f"\n{'=' * 50}")
    print(f"  FOLLOW-UP STATUS")
    print(f"{'=' * 50}")

    if results["needs_reply"]:
        print(f"\n  PENDING REPLIES ({len(results['needs_reply'])} — respond ASAP):")
        for r in results["needs_reply"]:
            print(f"    [{r['priority']}] {r['name']} via {r['channel']} — {r['age_hours']}h ago")

    if results["ready_touch_2"]:
        print(f"\n  READY FOR TOUCH 2 ({len(results['ready_touch_2'])} — 48h since touch 1):")
        for r in results["ready_touch_2"]:
            print(f"    {r['name']} via {r['channel']} — {r['days_since']}d since touch 1")

    if results["ready_touch_3"]:
        print(f"\n  READY FOR TOUCH 3 ({len(results['ready_touch_3'])} — 5d since touch 2):")
        for r in results["ready_touch_3"]:
            print(f"    {r['name']} via {r['channel']} — {r['days_since']}d since touch 2")

    if total_actions == 0:
        print(f"\n  No pending follow-ups.")

    print(f"\n{'=' * 50}")
    return total_actions


def outreach_scorecard(entries):
    """Weekly outreach metrics."""
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    this_week = [
        e for e in entries
        if e.get("date") and datetime.strptime(e["date"], "%Y-%m-%d") >= week_ago
    ]

    sent = len([e for e in this_week if e.get("status") in ["sent", "drafted"]])
    replied = len([e for e in this_week if e.get("status") in ["replied", "responded"]])
    reply_rate = round(replied / sent * 100, 1) if sent > 0 else 0

    print(f"\n  OUTREACH SCORECARD (last 7 days)")
    print(f"  DMs sent/drafted: {sent} (target: 210/week)")
    print(f"  Replies received: {replied}")
    print(f"  Reply rate: {reply_rate}%")

    if sent < 100:
        print(f"  *** BEHIND PACE — need {210 - sent} more this week ***")


def main():
    parser = argparse.ArgumentParser(description="Follow-up checker")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--overdue", action="store_true", help="Only show overdue")
    parser.add_argument("--scorecard", action="store_true", help="Show weekly scorecard")
    args = parser.parse_args()

    entries = load_log()

    if not entries:
        print("  No outreach data yet. Start sending DMs to populate.")
        return

    results = check_followups(entries, overdue_only=args.overdue)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_status(results)
        if args.scorecard:
            outreach_scorecard(entries)


if __name__ == "__main__":
    main()
