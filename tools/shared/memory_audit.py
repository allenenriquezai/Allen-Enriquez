"""
memory_audit.py — Daily lightweight memory health check.
Counts entries, flags stale project memories (>90 days), writes audit log.
Run by launchd daily at 6am. Zero LLM cost — pure file ops.
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude/projects/-Users-allenenriquez-Developer-Allen-Enriquez/memory"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
LOG_PATH = Path("/Users/allenenriquez/Developer/Allen-Enriquez/.tmp/memory_audit.log")
STALE_DAYS = 90


def parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            fm[k.strip()] = v.strip()
    return fm


def extract_date_from_content(text):
    matches = re.findall(r"\b(202\d-\d{2}-\d{2})\b", text)
    if matches:
        try:
            return datetime.strptime(matches[0], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def main():
    if not MEMORY_INDEX.exists():
        print("MEMORY.md not found — skipping audit")
        sys.exit(0)

    index_text = MEMORY_INDEX.read_text()
    entries = [l for l in index_text.splitlines() if l.strip().startswith("- [")]
    entry_count = len(entries)

    stale_flagged = 0
    today = date.today()

    for md_file in MEMORY_DIR.glob("*.md"):
        if md_file.name == "MEMORY.md":
            continue
        text = md_file.read_text()
        fm = parse_frontmatter(text)
        if fm.get("type") != "project":
            continue
        file_date = extract_date_from_content(text)
        if not file_date:
            continue
        age_days = (today - file_date).days
        if age_days > STALE_DAYS and "<!-- STALE" not in text:
            with open(md_file, "a") as f:
                f.write(f"\n<!-- STALE: {age_days}d old as of {today}. Review in /os-audit. -->")
            stale_flagged += 1

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_line = f"{today}: {entry_count} entries, 0 consolidated, {stale_flagged} flagged stale\n"
    with open(LOG_PATH, "a") as f:
        f.write(log_line)

    print(log_line.strip())

    if entry_count > 40:
        print(f"WARNING: {entry_count} memory entries — run /os-audit to consolidate")


if __name__ == "__main__":
    main()
