"""Migrate old flat Gmail labels → Ongoing/Unknown/Completed subfolders.

Old structure:  1. Projects/<ProjectName>
New structure:  1. Projects/Ongoing/<ProjectName>
                1. Projects/Unknown/<ProjectName>
                1. Projects/Completed/<ProjectName>

Usage:
    python3 migrate_labels.py            # dry-run (safe, shows what would change)
    python3 migrate_labels.py --execute  # apply changes to Gmail
"""
from __future__ import annotations
import argparse
import sys
import time
from typing import Optional

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
import registry


PROJECT_ROOT_PREFIX = "1. Projects/"
SUBFOLDERS = ("Ongoing/", "Unknown/", "Completed/")


def get_gmail_service():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_all_labels(svc) -> list[dict]:
    return svc.users().labels().list(userId="me").execute().get("labels", [])


def is_old_flat_label(label_name: str) -> bool:
    """Return True for 1. Projects/<Name> that aren't already in a subfolder."""
    if not label_name.startswith(PROJECT_ROOT_PREFIX):
        return False
    suffix = label_name[len(PROJECT_ROOT_PREFIX):]
    # Already migrated if it starts with a known subfolder
    for sub in SUBFOLDERS:
        if suffix.startswith(sub):
            return False
    # Skip if it's just the root label itself (no project name)
    if not suffix.strip():
        return False
    return True


def target_label_for(project_name: str) -> str:
    """Determine new label path by looking up project status in registry."""
    proj = registry.find_project(project_name)
    if proj:
        status = proj.get("status", "unknown")
    else:
        status = "unknown"

    rules = config.load_routing_rules()
    bucket = rules["buckets"]["project"]
    if status == "active":
        prefix = bucket.get("label_prefix_active", "1. Projects/Ongoing/")
    elif status == "completed":
        prefix = bucket.get("label_prefix_completed", "1. Projects/Completed/")
    else:
        prefix = bucket.get("label_prefix_unknown", "1. Projects/Unknown/")
    return f"{prefix}{project_name}"


def get_or_create_label(svc, name: str, all_labels: list[dict], dry_run: bool) -> Optional[str]:
    for lbl in all_labels:
        if lbl["name"] == name:
            return lbl["id"]
    if dry_run:
        return f"<would-create:{name}>"
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = svc.users().labels().create(userId="me", body=body).execute()
    all_labels.append({"id": created["id"], "name": name})
    return created["id"]


def get_message_ids_for_label(svc, label_id: str) -> list[str]:
    """Paginate through all messages with this label."""
    ids = []
    page_token = None
    while True:
        kwargs = {"userId": "me", "labelIds": [label_id], "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.users().messages().list(**kwargs).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def batch_relabel(svc, message_ids: list[str], add_id: str, remove_id: str, dry_run: bool) -> int:
    """Add new label and remove old label from all messages. Returns count modified."""
    if dry_run or not message_ids:
        return len(message_ids)
    modified = 0
    for msg_id in message_ids:
        try:
            svc.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"addLabelIds": [add_id], "removeLabelIds": [remove_id]},
            ).execute()
            modified += 1
        except HttpError as e:
            print(f"  WARNING: modify failed for {msg_id}: {e}")
        time.sleep(0.05)  # stay well under Gmail API rate limit
    return modified


def delete_label(svc, label_id: str, dry_run: bool) -> None:
    if dry_run:
        return
    svc.users().labels().delete(userId="me", id=label_id).execute()


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== Label migration — {mode} ===\n")

    svc = get_gmail_service()
    all_labels = list_all_labels(svc)

    old_labels = [lbl for lbl in all_labels if is_old_flat_label(lbl["name"])]
    if not old_labels:
        print("No flat project labels found. Already migrated or nothing to migrate.")
        return

    print(f"Found {len(old_labels)} flat label(s) to migrate:\n")

    total_messages = 0
    migrations = []

    for lbl in old_labels:
        project_name = lbl["name"][len(PROJECT_ROOT_PREFIX):]
        new_label_name = target_label_for(project_name)
        msg_ids = get_message_ids_for_label(svc, lbl["id"])
        migrations.append({
            "old_name": lbl["name"],
            "old_id": lbl["id"],
            "new_name": new_label_name,
            "msg_ids": msg_ids,
        })
        total_messages += len(msg_ids)
        print(f"  {lbl['name']!r}")
        print(f"    → {new_label_name!r}  ({len(msg_ids)} message{'s' if len(msg_ids) != 1 else ''})")

    print(f"\nTotal: {len(old_labels)} labels, {total_messages} messages")

    if dry_run:
        print("\nDry run complete. Run with --execute to apply.")
        return

    print("\nApplying...")
    for m in migrations:
        new_id = get_or_create_label(svc, m["new_name"], all_labels, dry_run=False)
        if new_id is None:
            print(f"  SKIP (could not create label): {m['new_name']}")
            continue
        count = batch_relabel(svc, m["msg_ids"], add_id=new_id, remove_id=m["old_id"], dry_run=False)
        delete_label(svc, m["old_id"], dry_run=False)
        print(f"  ✓ {m['old_name']!r} → {m['new_name']!r}  ({count} messages moved, old label deleted)")

    print("\nMigration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate flat Gmail project labels to Ongoing/Unknown subfolders.")
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run only)")
    args = parser.parse_args()
    run(dry_run=not args.execute)
