#!/usr/bin/env python3
"""
Intel freshness checker for Enriquez OS.
Checks last_updated dates in reference/intel/ docs and flags stale ones.

Usage:
    python3 tools/intel_freshness.py          # Check all intel docs
    python3 tools/intel_freshness.py --json   # Output as JSON (for /start skill)
"""

import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEL_DIR = PROJECT_ROOT / "projects" / "personal" / "reference" / "intel"

# Max age before flagging as stale (days)
STALE_THRESHOLDS = {
    "market-validation.md": 14,  # biweekly is fine
}
DEFAULT_STALE_DAYS = 7


def check_freshness():
    results = []
    now = datetime.now()

    if not INTEL_DIR.exists():
        print("  Intel directory not found")
        return results

    for f in sorted(INTEL_DIR.glob("*.md")):
        name = f.name
        threshold = STALE_THRESHOLDS.get(name, DEFAULT_STALE_DAYS)

        # Read first 5 lines for last_updated
        with open(f) as fh:
            head = fh.read(500)

        # Look for "Last updated: YYYY-MM-DD" pattern
        match = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", head)
        if match:
            updated = datetime.strptime(match.group(1), "%Y-%m-%d")
            age_days = (now - updated).days
            stale = age_days > threshold
        else:
            # No date found — treat as stale
            age_days = -1
            stale = True
            updated = None

        results.append({
            "file": name,
            "last_updated": updated.strftime("%Y-%m-%d") if updated else "never",
            "age_days": age_days,
            "threshold_days": threshold,
            "stale": stale,
        })

    return results


def print_status(results):
    fresh = [r for r in results if not r["stale"]]
    stale = [r for r in results if r["stale"]]
    total = len(results)

    print(f"\nIntel: {len(fresh)}/{total} docs fresh", end="")
    if stale:
        stale_list = ", ".join(
            f"{r['file']} ({r['age_days']}d)" if r['age_days'] >= 0
            else f"{r['file']} (no date)"
            for r in stale
        )
        print(f" | STALE: {stale_list}")
    else:
        print()


def main():
    parser = argparse.ArgumentParser(description="Check intel doc freshness")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = check_freshness()

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print_status(results)


if __name__ == "__main__":
    main()
