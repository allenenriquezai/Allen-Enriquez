"""One-time migration: rename label prefixes to include a./b./c. sort order.

Renames:
  1. Projects/Ongoing   → 1. Projects/a. Ongoing
  1. Projects/Completed → 1. Projects/b. Completed
  1. Projects/Unknown   → 1. Projects/c. Unknown
  1. Projects/Ongoing/* → 1. Projects/a. Ongoing/*
  1. Projects/Unknown/* → 1. Projects/c. Unknown/*

Usage:
    python3 fix_label_prefixes.py            # dry-run
    python3 fix_label_prefixes.py --execute  # apply
"""
from __future__ import annotations
import argparse
import time

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

RENAMES = [
    ("1. Projects/Ongoing",   "1. Projects/a. Ongoing"),
    ("1. Projects/Completed", "1. Projects/b. Completed"),
    ("1. Projects/Unknown",   "1. Projects/c. Unknown"),
]
OLD_PREFIXES = [
    ("1. Projects/Ongoing/",   "1. Projects/a. Ongoing/"),
    ("1. Projects/Unknown/",   "1. Projects/c. Unknown/"),
    ("1. Projects/Completed/", "1. Projects/b. Completed/"),
]


def get_svc():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== fix_label_prefixes — {mode} ===\n")

    svc = get_svc()
    all_labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label_by_name = {l["name"]: l for l in all_labels}

    # --- Step 1: rename folder labels (no messages attached) ---
    print("── Folder labels ──")
    for old_name, new_name in RENAMES:
        lbl = label_by_name.get(old_name)
        if not lbl:
            print(f"  SKIP (not found): {old_name}")
            continue
        print(f"  {old_name} → {new_name}")
        if not dry_run:
            if new_name not in label_by_name:
                created = svc.users().labels().create(userId="me", body={
                    "name": new_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                }).execute()
                label_by_name[new_name] = created
            svc.users().labels().delete(userId="me", id=lbl["id"]).execute()
            del label_by_name[old_name]

    # --- Step 2: rename project leaf labels + move messages ---
    print("\n── Project labels ──")
    for old_prefix, new_prefix in OLD_PREFIXES:
        targets = [l for l in all_labels if l["name"].startswith(old_prefix)]
        if not targets:
            continue
        print(f"\n  {old_prefix} ({len(targets)} labels)")
        for lbl in targets:
            old_name = lbl["name"]
            new_name = new_prefix + old_name[len(old_prefix):]
            print(f"    {old_name} → {new_name}", end="")

            # Count messages
            resp = svc.users().messages().list(
                userId="me", labelIds=[lbl["id"]], maxResults=1
            ).execute()
            msg_count = resp.get("resultSizeEstimate", 0)
            print(f" [{msg_count} msgs]")

            if dry_run:
                continue

            # Create new label
            if new_name in label_by_name:
                new_id = label_by_name[new_name]["id"]
            else:
                created = svc.users().labels().create(userId="me", body={
                    "name": new_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                }).execute()
                new_id = created["id"]
                label_by_name[new_name] = created

            # Paginate + move messages
            page_token = None
            moved = 0
            while True:
                kwargs = {"userId": "me", "labelIds": [lbl["id"]], "maxResults": 500}
                if page_token:
                    kwargs["pageToken"] = page_token
                page = svc.users().messages().list(**kwargs).execute()
                for m in page.get("messages", []):
                    try:
                        svc.users().messages().modify(
                            userId="me", id=m["id"],
                            body={"addLabelIds": [new_id], "removeLabelIds": [lbl["id"]]},
                        ).execute()
                        moved += 1
                    except HttpError as e:
                        print(f"      WARNING: {m['id']} failed: {e}")
                    time.sleep(0.04)
                page_token = page.get("nextPageToken")
                if not page_token:
                    break

            # Delete old label
            try:
                svc.users().labels().delete(userId="me", id=lbl["id"]).execute()
                print(f"      moved {moved}, deleted old label")
            except HttpError as e:
                print(f"      moved {moved}, WARNING delete failed: {e}")

    if dry_run:
        print("\nDry run complete. Run with --execute to apply.")
    else:
        print("\nMigration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.execute)
