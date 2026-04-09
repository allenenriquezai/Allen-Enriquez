"""
Clean and categorize bbb_leads_nc.csv.

Fixes:
  - Strips "advertisement:\\n" prefix from business_name
  - Extracts real BBB URL from DoubleClick ad redirect URLs
  - Deduplicates by normalized business name
  - Clears junk share-link emails

Outputs:
  ~/Desktop/bbb_painting_nc.csv   — names containing paint/painting/painter
  ~/Desktop/bbb_other_nc.csv      — everything else (construction, handyman, etc.)
"""

import csv
import re
import urllib.parse
from pathlib import Path

INPUT = Path.home() / "Desktop" / "bbb_leads_nc.csv"
OUT_PAINTING = Path.home() / "Desktop" / "bbb_painting_nc.csv"
OUT_OTHER = Path.home() / "Desktop" / "bbb_other_nc.csv"

PAINTING_RE = re.compile(r"\bpaint(ing|er|s)?\b", re.IGNORECASE)


def fix_name(name: str) -> str:
    """Strip 'advertisement:\\n' or similar ad prefixes."""
    name = re.sub(r"^advertisement:\s*\n?", "", name, flags=re.IGNORECASE)
    return name.strip().strip('"')


def extract_bbb_url(url: str) -> str:
    """If URL is a DoubleClick redirect, pull the real BBB URL from adurl=."""
    if "doubleclick.net" in url or "adclick" in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        adurl = params.get("adurl", [""])[0]
        if adurl and "bbb.org" in adurl:
            return adurl
        # Try to find bbb.org anywhere in the URL
        match = re.search(r"(https://www\.bbb\.org/[^\s&\"]+)", url)
        if match:
            return match.group(1)
    return url


def fix_email(email: str) -> str:
    """Discard BBB share-link pseudo-emails."""
    if email.startswith("?body=") or "Check%20out%20this%20page" in email:
        return ""
    return email


def dedup_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main():
    rows = []
    seen = set()

    with open(INPUT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["business_name"] = fix_name(row["business_name"])
            row["profile_url"] = extract_bbb_url(row["profile_url"])
            row["email"] = fix_email(row.get("email", ""))

            key = dedup_key(row["business_name"])
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(row)

    painting = [r for r in rows if PAINTING_RE.search(r["business_name"])]
    other = [r for r in rows if not PAINTING_RE.search(r["business_name"])]

    fieldnames = list(rows[0].keys())

    for path, data in [(OUT_PAINTING, painting), (OUT_OTHER, other)]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    print(f"Total unique: {len(rows)}")
    print(f"  Painting:  {len(painting):>4}  → {OUT_PAINTING.name}")
    print(f"  Other:     {len(other):>4}  → {OUT_OTHER.name}")


if __name__ == "__main__":
    main()
