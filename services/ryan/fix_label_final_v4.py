"""Final label restructure — one clean pass.

Changes:
  3. Office          → 2. Team/Office  (move under Team parent)
  4. Vendors/Pricing → 3. Vendors/Pricing
  5. Bids/Invites    → 4. Bids/Invites
  6. Archive/Promos  → 5. Archive/Promos
  6. Archive/Review  → 5. Archive/Review

Orphan cleanup (empty parent folders):
  Delete: 3. Bids, 3. Office (after emptied), 4. Vendors, 5. Archive

Usage:
    python3 fix_label_final_v4.py            # dry-run
    python3 fix_label_final_v4.py --execute  # apply
"""
from __future__ import annotations
import argparse
import time

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

RENAMES = [
    ("3. Office",          "2. Team/Office"),
    ("4. Vendors/Pricing", "3. Vendors/Pricing"),
    ("5. Bids/Invites",    "4. Bids/Invites"),
    ("6. Archive/Promos",  "5. Archive/Promos"),
    ("6. Archive/Review",  "5. Archive/Review"),
]

ORPHANS_TO_DELETE = ["3. Bids", "3. Office", "4. Vendors", "5. Archive"]


def get_svc():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def msg_count(svc, label_id: str) -> int:
    r = svc.users().messages().list(userId="me", labelIds=[label_id], maxResults=1).execute()
    return r.get("resultSizeEstimate", 0)


def move_messages(svc, old_id: str, new_id: str) -> int:
    moved = 0
    page_token = None
    while True:
        kwargs = {"userId": "me", "labelIds": [old_id], "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        page = svc.users().messages().list(**kwargs).execute()
        for m in page.get("messages", []):
            try:
                svc.users().messages().modify(
                    userId="me", id=m["id"],
                    body={"addLabelIds": [new_id], "removeLabelIds": [old_id]},
                ).execute()
                moved += 1
            except HttpError as e:
                print(f"    WARNING {m['id']}: {e}")
            time.sleep(0.04)
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    return moved


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== fix_label_final_v4 — {mode} ===\n")

    svc = get_svc()
    all_labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    by_name = {l["name"]: l for l in all_labels}

    # ── Step 1: Renames ───────────────────────────────────────────────────────
    print("── Renames ──")
    for old_name, new_name in RENAMES:
        lbl = by_name.get(old_name)
        if not lbl:
            print(f"  SKIP (not found): {old_name}")
            continue
        count = msg_count(svc, lbl["id"])
        print(f"  {old_name} → {new_name}  [{count} msgs]")
        if dry_run:
            continue

        if new_name not in by_name:
            created = svc.users().labels().create(userId="me", body={
                "name": new_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }).execute()
            by_name[new_name] = created
            new_id = created["id"]
        else:
            new_id = by_name[new_name]["id"]

        moved = move_messages(svc, lbl["id"], new_id)
        try:
            svc.users().labels().delete(userId="me", id=lbl["id"]).execute()
            del by_name[old_name]
            print(f"    moved {moved}, deleted ✓")
        except HttpError as e:
            print(f"    moved {moved}, delete failed: {e}")

    # ── Step 2: Orphan cleanup ────────────────────────────────────────────────
    print("\n── Orphan cleanup ──")
    for name in ORPHANS_TO_DELETE:
        lbl = by_name.get(name)
        if not lbl:
            print(f"  SKIP (not found): {name}")
            continue
        count = msg_count(svc, lbl["id"])
        print(f"  Delete: {name}  [{count} msgs]", end="")
        if count > 0:
            print(f"  ⚠ NOT EMPTY — skipping (investigate manually)")
            continue
        print()
        if dry_run:
            continue
        try:
            svc.users().labels().delete(userId="me", id=lbl["id"]).execute()
            print(f"    deleted ✓")
        except HttpError as e:
            print(f"    delete failed: {e}")

    if dry_run:
        print("\nDry run complete. Run with --execute to apply.")
    else:
        print("\nMigration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.execute)
