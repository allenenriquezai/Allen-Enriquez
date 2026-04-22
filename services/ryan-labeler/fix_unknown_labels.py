"""One-time migration: rename 1. Projects/Unknown/* labels → 1. Projects/Ongoing/*.

Steps:
1. Find all labels matching "1. Projects/Unknown/"
2. For each, find or create the "1. Projects/Ongoing/" equivalent
3. Move all messages from Unknown → Ongoing label
4. Delete the old Unknown label

Usage:
    python3 fix_unknown_labels.py            # dry-run
    python3 fix_unknown_labels.py --execute  # apply
"""
from __future__ import annotations
import argparse
import time

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

UNKNOWN_PREFIX = "1. Projects/Unknown/"
ONGOING_PREFIX = "1. Projects/Ongoing/"


def get_svc():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== fix_unknown_labels — {mode} ===\n")

    svc = get_svc()
    all_labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label_by_name = {l["name"]: l["id"] for l in all_labels}

    unknown_labels = [l for l in all_labels if l["name"].startswith(UNKNOWN_PREFIX)]
    print(f"Found {len(unknown_labels)} Unknown/* labels to migrate\n")

    if not unknown_labels:
        print("Nothing to do.")
        return

    for lbl in unknown_labels:
        old_name = lbl["name"]
        old_id = lbl["id"]
        project_part = old_name[len(UNKNOWN_PREFIX):]
        new_name = ONGOING_PREFIX + project_part

        print(f"  {old_name}")
        print(f"  → {new_name}")

        # Paginate messages with this label
        msg_ids = []
        page_token = None
        while True:
            kwargs = {"userId": "me", "labelIds": [old_id], "maxResults": 500}
            if page_token:
                kwargs["pageToken"] = page_token
            resp = svc.users().messages().list(**kwargs).execute()
            msg_ids.extend(m["id"] for m in resp.get("messages", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        print(f"  {len(msg_ids)} messages")

        if dry_run:
            print()
            continue

        # Find or create new Ongoing label
        if new_name in label_by_name:
            new_id = label_by_name[new_name]
        else:
            created = svc.users().labels().create(userId="me", body={
                "name": new_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }).execute()
            new_id = created["id"]
            label_by_name[new_name] = new_id

        # Move messages
        moved = 0
        for mid in msg_ids:
            try:
                svc.users().messages().modify(
                    userId="me", id=mid,
                    body={"addLabelIds": [new_id], "removeLabelIds": [old_id]},
                ).execute()
                moved += 1
            except HttpError as e:
                print(f"    WARNING: {mid} failed: {e}")
            time.sleep(0.05)

        print(f"  Moved {moved}/{len(msg_ids)}")

        # Delete old Unknown label (only if all messages moved)
        if moved == len(msg_ids):
            try:
                svc.users().labels().delete(userId="me", id=old_id).execute()
                print(f"  Deleted old label: {old_name}")
            except HttpError as e:
                print(f"  WARNING: could not delete old label: {e}")
        else:
            print(f"  Skipped delete — not all messages moved ({moved}/{len(msg_ids)})")

        print()

    if dry_run:
        print("Dry run complete. Run with --execute to apply.")
    else:
        print("Migration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.execute)
