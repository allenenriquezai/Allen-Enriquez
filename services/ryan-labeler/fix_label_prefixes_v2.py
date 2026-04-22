"""One-time migration: rename label prefixes from a./b./c. to A./B./C./D. + add Upcoming.

Renames:
  1. Projects/a. Ongoing   → 1. Projects/B. Ongoing
  1. Projects/b. Completed → 1. Projects/C. Completed
  1. Projects/c. Unknown   → 1. Projects/D. Unknown

Creates:
  1. Projects/A. Upcoming  (new folder, no messages)

Renames leaf labels + moves messages:
  1. Projects/a. Ongoing/*   → 1. Projects/B. Ongoing/*
  1. Projects/b. Completed/* → 1. Projects/C. Completed/*
  1. Projects/c. Unknown/*   → 1. Projects/D. Unknown/*

Usage:
    python3 fix_label_prefixes_v2.py            # dry-run
    python3 fix_label_prefixes_v2.py --execute  # apply
"""
from __future__ import annotations
import argparse
import time

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

RENAMES = [
    ("1. Projects/a. Ongoing",   "1. Projects/B. Ongoing"),
    ("1. Projects/b. Completed", "1. Projects/C. Completed"),
    ("1. Projects/c. Unknown",   "1. Projects/D. Unknown"),
]

NEW_FOLDERS = [
    "1. Projects/A. Upcoming",
]

OLD_PREFIXES = [
    ("1. Projects/a. Ongoing/",   "1. Projects/B. Ongoing/"),
    ("1. Projects/b. Completed/", "1. Projects/C. Completed/"),
    ("1. Projects/c. Unknown/",   "1. Projects/D. Unknown/"),
]


def get_svc():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== fix_label_prefixes_v2 — {mode} ===\n")

    svc = get_svc()
    all_labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label_by_name = {l["name"]: l for l in all_labels}

    # --- Step 1: rename existing folder labels ---
    print("── Folder renames ──")
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

    # --- Step 2: create new folder labels ---
    print("\n── New folders ──")
    for name in NEW_FOLDERS:
        if name in label_by_name:
            print(f"  Already exists: {name}")
        else:
            print(f"  Create: {name}")
            if not dry_run:
                created = svc.users().labels().create(userId="me", body={
                    "name": name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                }).execute()
                label_by_name[name] = created

    # --- Step 3: rename leaf labels + move messages ---
    print("\n── Leaf labels ──")
    for old_prefix, new_prefix in OLD_PREFIXES:
        targets = [l for l in all_labels if l["name"].startswith(old_prefix)]
        if not targets:
            print(f"\n  {old_prefix} — none found")
            continue
        print(f"\n  {old_prefix} ({len(targets)} labels)")
        for lbl in targets:
            old_name = lbl["name"]
            new_name = new_prefix + old_name[len(old_prefix):]
            print(f"    {old_name} → {new_name}", end="")

            resp = svc.users().messages().list(
                userId="me", labelIds=[lbl["id"]], maxResults=1
            ).execute()
            msg_count = resp.get("resultSizeEstimate", 0)
            print(f" [{msg_count} msgs]")

            if dry_run:
                continue

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
