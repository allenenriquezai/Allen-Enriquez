"""Gmail label creation + message labeling.

Handles:
- Find/create Gmail labels on demand (including nested labels like Projects/Pura Vida)
- Apply labels + optionally remove INBOX (skip-inbox buckets)
- Mark as IMPORTANT for priority overrides
- Fetch message metadata for classifier input
"""
from __future__ import annotations
from typing import Optional

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
import registry


_gmail_service = None
_label_cache: dict[str, str] = {}  # label_name -> label_id


def get_gmail_service():
    """Build Gmail service using Ryan's OAuth creds. Refreshes token if needed."""
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    _gmail_service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _gmail_service


def get_or_create_label(name: str) -> str:
    """Return label ID, creating if missing. Caches in-process."""
    if name in _label_cache:
        return _label_cache[name]

    service = get_gmail_service()
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == name:
            _label_cache[name] = lbl["id"]
            return lbl["id"]

    # Create
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    _label_cache[name] = created["id"]
    return created["id"]


def fetch_message(message_id: str) -> dict:
    """Fetch message metadata + snippet for classifier input."""
    service = get_gmail_service()
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="metadata",
        metadataHeaders=["From", "To", "Subject", "Date", "List-Unsubscribe"],
    ).execute()
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "label_ids": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "has_unsubscribe": bool(headers.get("list-unsubscribe")),
    }


def apply_labels(
    message_id: str,
    add_label_ids: list[str],
    remove_label_ids: Optional[list[str]] = None,
) -> dict:
    """Apply labels to a message via users.messages.modify."""
    service = get_gmail_service()
    body = {"addLabelIds": add_label_ids}
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids
    return service.users().messages().modify(
        userId="me", id=message_id, body=body
    ).execute()


def route_and_label(message_id: str, classification: dict, dry_run: bool = False) -> dict:
    """Main entry: given a classification, apply the right Gmail labels.

    Returns a dict describing what was done (bucket, labels applied, skip_inbox).
    """
    rules = config.load_routing_rules()
    buckets = rules["buckets"]
    category = classification["category"]
    bucket_cfg = buckets.get(category, buckets["other"])

    labels_to_add: list[str] = []
    labels_to_remove: list[str] = []
    project = None

    # Category label
    if bucket_cfg.get("label_prefix"):
        # project bucket — need project label
        project = registry.find_project(classification.get("project_hint") or "")
        if project is None and classification.get("project_hint") and classification["confidence"] >= 0.7:
            if not dry_run:
                project = registry.create_project(classification["project_hint"])
            else:
                # Synthesize ephemeral project for preview only (not persisted)
                project = {
                    "id": registry._slugify(classification["project_hint"]),
                    "display_name": classification["project_hint"].strip()[:80],
                    "label_id": None,
                    "_ephemeral": True,
                }
        if project:
            label_name = registry.project_label_name(project)
            if not dry_run:
                label_id = get_or_create_label(label_name)
                labels_to_add.append(label_id)
                if not project.get("label_id"):
                    registry.update_label_id(project["id"], label_id)
            else:
                labels_to_add.append(f"<would-create:{label_name}>")
        else:
            # project category but no hint — treat as needs-review
            fallback = buckets["other"]["label"]
            if fallback and not dry_run:
                labels_to_add.append(get_or_create_label(fallback))
    elif bucket_cfg.get("label"):
        if not dry_run:
            labels_to_add.append(get_or_create_label(bucket_cfg["label"]))
        else:
            labels_to_add.append(f"<would-create:{bucket_cfg['label']}>")

    # Any bucket: if project_hint resolves to a known project, also apply project label
    if classification.get("project_hint"):
        xp = registry.find_project(classification["project_hint"])
        if xp:
            xp_name = registry.project_label_name(xp)
            if not dry_run:
                labels_to_add.append(get_or_create_label(xp_name))
            else:
                labels_to_add.append(f"<would-create:{xp_name}>")

    # Skip-inbox buckets remove INBOX
    skip_inbox = bucket_cfg.get("skip_inbox", False)
    if skip_inbox:
        labels_to_remove.append("INBOX")

    # Priority override — mark IMPORTANT for everything except bid_invite/vendor
    if category not in ("bid_invite", "vendor", "promo"):
        labels_to_add.append("IMPORTANT")

    # De-dupe
    labels_to_add = list(dict.fromkeys(labels_to_add))

    if dry_run:
        return {
            "dry_run": True,
            "message_id": message_id,
            "bucket": category,
            "project": project["id"] if project else None,
            "would_add": labels_to_add,
            "would_remove": labels_to_remove,
            "skip_inbox": skip_inbox,
        }

    try:
        apply_labels(message_id, labels_to_add, labels_to_remove or None)
        applied = True
        error = None
    except HttpError as e:
        applied = False
        error = str(e)

    return {
        "dry_run": False,
        "message_id": message_id,
        "bucket": category,
        "project": project["id"] if project else None,
        "labels_added": labels_to_add,
        "labels_removed": labels_to_remove,
        "skip_inbox": skip_inbox,
        "applied": applied,
        "error": error,
    }
