"""Audit Ryan's Gmail labels — spot mislabeled emails across all buckets.

Fetches messages under each custom label, cross-refs with Haiku classifications,
flags suspicious sender/category pairs, and writes a CSV for review.

Usage:
    python3 tools/ryan_label_audit.py
    python3 tools/ryan_label_audit.py --label "2. Team/Daily Accomplishments PH"
    python3 tools/ryan_label_audit.py --flagged-only
    python3 tools/ryan_label_audit.py --max-per-label 200
"""
from __future__ import annotations

import argparse
import csv
import json
import pickle
import re
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = REPO_ROOT / "projects/personal/clients/ryan/token_ryan.pickle"
CLASSIFICATIONS_FILE = REPO_ROOT / "projects/personal/clients/ryan/classifications.json"
OUTPUT_CSV = REPO_ROOT / "projects/personal/clients/ryan/label_audit.csv"

OUR_LABEL_PREFIXES = [
    "1. Projects",
    "2. Team",
    "3. Bids",
    "4. Vendors",
    "5. Archive",
]

VENDOR_DOMAINS = {
    "daltile.com", "bedrosians.com", "caesarstone.com", "lxhausys.com",
    "cosentino.com", "emser.com", "arizonatile.com", "coronadostone.com",
}

INTERNAL_DOMAIN = "sc-incorporated.com"
KIM_PATTERN = re.compile(r"kim\s+bayudan|stonework\s+contracting|kimstyle", re.I)

EMAIL_RE = re.compile(r"<([^>]+)>|([^\s<>]+@[^\s<>]+)")


def load_creds():
    if not TOKEN_FILE.exists():
        sys.exit(f"Token not found: {TOKEN_FILE}")
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def parse_email(raw: str) -> tuple[str, str]:
    """Returns (display, email_lower)."""
    m = EMAIL_RE.search(raw or "")
    email = (m.group(1) or m.group(2) or "").strip().lower() if m else ""
    domain = email.split("@")[-1] if "@" in email else ""
    return email, domain


def flag_message(label_name: str, from_raw: str, haiku_cat: str) -> str | None:
    """Return flag reason string, or None if clean."""
    email, domain = parse_email(from_raw)

    if label_name.startswith("2. Team"):
        if domain != INTERNAL_DOMAIN and not KIM_PATTERN.search(from_raw):
            return f"team label but external sender ({domain or email})"

    elif label_name.startswith("3. Bids"):
        if domain == INTERNAL_DOMAIN and "joseph" not in email:
            return f"bid label but internal non-Joseph sender ({email})"

    elif label_name.startswith("4. Vendors"):
        if domain not in VENDOR_DOMAINS and domain != INTERNAL_DOMAIN:
            return f"vendor label but unknown domain ({domain or email})"

    elif label_name.startswith("1. Projects"):
        if haiku_cat in ("vendor", "bid_invite", "promo"):
            return f"project label but Haiku said '{haiku_cat}'"

    elif label_name.startswith("5. Archive/Review"):
        return "needs-review bucket — low confidence"

    return None


def list_messages_for_label(service, label_id: str, max_results: int) -> list[str]:
    ids = []
    page_token = None
    while len(ids) < max_results:
        resp = service.users().messages().list(
            userId="me", labelIds=[label_id],
            maxResults=min(500, max_results - len(ids)),
            pageToken=page_token,
        ).execute()
        for m in resp.get("messages", []):
            ids.append(m["id"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def fetch_metadata_batch(service, ids: list[str]) -> list[dict]:
    results = []

    def cb(req_id, response, exception):
        if response:
            results.append(response)

    batch_size = 20
    for i in range(0, len(ids), batch_size):
        chunk = ids[i:i + batch_size]
        batch = service.new_batch_http_request(callback=cb)
        for mid in chunk:
            batch.add(service.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["From", "Subject"],
            ))
        for attempt in range(3):
            try:
                batch.execute()
                break
            except HttpError as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(2 ** attempt + 1)
                else:
                    print(f"  batch error: {e}", file=sys.stderr)
                    break
        time.sleep(0.15)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=None, help="Audit only this specific label name")
    ap.add_argument("--flagged-only", action="store_true", help="Only show flagged rows")
    ap.add_argument("--max-per-label", type=int, default=500)
    args = ap.parse_args()

    if not CLASSIFICATIONS_FILE.exists():
        sys.exit(f"Classifications not found: {CLASSIFICATIONS_FILE}")
    classifications: dict[str, dict] = json.loads(CLASSIFICATIONS_FILE.read_text())
    print(f"Loaded {len(classifications)} classifications")

    creds = load_creds()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    all_labels = service.users().labels().list(userId="me").execute().get("labels", [])
    our_labels = [
        lbl for lbl in all_labels
        if any(lbl["name"].startswith(p) for p in OUR_LABEL_PREFIXES)
    ]

    if args.label:
        our_labels = [l for l in our_labels if l["name"] == args.label]
        if not our_labels:
            sys.exit(f"Label not found: {args.label}")

    print(f"Auditing {len(our_labels)} labels\n")

    rows = []
    label_summary: dict[str, dict] = {}

    for lbl in sorted(our_labels, key=lambda x: x["name"]):
        name = lbl["name"]
        lid = lbl["id"]
        print(f"  {name} ...", end="", flush=True)

        ids = list_messages_for_label(service, lid, args.max_per_label)
        if not ids:
            print(" (empty)")
            label_summary[name] = {"total": 0, "flagged": 0}
            continue

        raw_msgs = fetch_metadata_batch(service, ids)
        flagged_count = 0

        for raw in raw_msgs:
            mid = raw["id"]
            headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
            from_raw = headers.get("from", "")
            subject = headers.get("subject", "")
            haiku = classifications.get(mid, {})
            haiku_cat = haiku.get("category", "unknown")
            flag = flag_message(name, from_raw, haiku_cat)
            if flag:
                flagged_count += 1

            if not args.flagged_only or flag:
                rows.append({
                    "label": name,
                    "from": from_raw[:120],
                    "subject": subject[:120],
                    "haiku_category": haiku_cat,
                    "flag": flag or "",
                })

        label_summary[name] = {"total": len(raw_msgs), "flagged": flagged_count}
        print(f" {len(raw_msgs)} msgs, {flagged_count} flagged")

    # Console summary
    print("\n=== Summary ===")
    total_msgs = sum(v["total"] for v in label_summary.values())
    total_flagged = sum(v["flagged"] for v in label_summary.values())
    print(f"Total messages audited : {total_msgs}")
    print(f"Total flagged          : {total_flagged}")
    print()
    for name, s in sorted(label_summary.items()):
        flag_str = f"  ← {s['flagged']} FLAGGED" if s["flagged"] else ""
        print(f"  {name:<45} {s['total']:>4} msgs{flag_str}")

    # Flagged detail
    flagged_rows = [r for r in rows if r["flag"]]
    if flagged_rows:
        print(f"\n=== Flagged ({len(flagged_rows)}) ===")
        for r in flagged_rows[:100]:
            print(f"  [{r['label']}]")
            print(f"    From   : {r['from']}")
            print(f"    Subject: {r['subject']}")
            print(f"    Haiku  : {r['haiku_category']}")
            print(f"    Flag   : {r['flag']}")
            print()

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "from", "subject", "haiku_category", "flag"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV written: {OUTPUT_CSV}")
    print(f"Rows: {len(rows)} total, {len(flagged_rows)} flagged")


if __name__ == "__main__":
    main()
