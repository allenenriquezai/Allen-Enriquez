"""Gmail label creation + message labeling.

Multi-mailbox: same module serves multiple SC inboxes (Ryan, Joseph). Pass
`mailbox` ("ryan" | "joseph") to every public function. Gmail service singleton
and label-id cache are keyed per-mailbox so each inbox holds its own auth.

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


_gmail_services: dict[str, object] = {}              # mailbox -> Gmail service
_label_caches: dict[str, dict[str, str]] = {}        # mailbox -> {label_name: label_id}


def get_gmail_service(mailbox: str = config.DEFAULT_MAILBOX):
    """Build Gmail service for the given mailbox. Refreshes token if needed."""
    svc = _gmail_services.get(mailbox)
    if svc is not None:
        return svc
    creds = config.gmail_creds(mailbox)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    _gmail_services[mailbox] = svc
    return svc


def _label_cache(mailbox: str) -> dict[str, str]:
    cache = _label_caches.get(mailbox)
    if cache is None:
        cache = {}
        _label_caches[mailbox] = cache
    return cache


def get_or_create_label(name: str, mailbox: str = config.DEFAULT_MAILBOX) -> str:
    """Return label ID, creating if missing. Caches in-process per mailbox."""
    cache = _label_cache(mailbox)
    if name in cache:
        return cache[name]

    service = get_gmail_service(mailbox)
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == name:
            cache[name] = lbl["id"]
            return lbl["id"]

    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    cache[name] = created["id"]
    return created["id"]


def fetch_message(message_id: str, mailbox: str = config.DEFAULT_MAILBOX) -> dict:
    """Fetch message metadata + snippet for classifier input."""
    service = get_gmail_service(mailbox)
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
    mailbox: str = config.DEFAULT_MAILBOX,
) -> dict:
    """Apply labels to a message via users.messages.modify."""
    service = get_gmail_service(mailbox)
    body = {"addLabelIds": add_label_ids}
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids
    return service.users().messages().modify(
        userId="me", id=message_id, body=body
    ).execute()


def route_and_label(
    message_id: str,
    classification: dict,
    dry_run: bool = False,
    mailbox: str = config.DEFAULT_MAILBOX,
) -> dict:
    """Main entry: given a classification, apply the right Gmail labels.

    Returns a dict describing what was done (bucket, labels applied, skip_inbox).
    """
    rules = config.load_routing_rules(mailbox)
    buckets = rules["buckets"]
    category = classification["category"]
    bucket_cfg = buckets.get(category, buckets["other"])

    labels_to_add: list[str] = []
    labels_to_remove: list[str] = []
    project = None

    # Category label — project bucket has label_prefix_*; flat buckets have `label`
    if bucket_cfg.get("label_prefix"):
        project = registry.find_project(classification.get("project_hint") or "")
        if project is None and classification.get("project_hint") and classification["confidence"] >= 0.7:
            if not dry_run:
                project = registry.create_project(classification["project_hint"])
            else:
                project = {
                    "id": registry._slugify(classification["project_hint"]),
                    "display_name": classification["project_hint"].strip()[:80],
                    "label_id": None,
                    "_ephemeral": True,
                }
        if project:
            label_name = registry.project_label_name(project)
            if not dry_run:
                label_id = get_or_create_label(label_name, mailbox=mailbox)
                labels_to_add.append(label_id)
                if not project.get("label_id"):
                    registry.update_label_id(project["id"], label_id)
            else:
                labels_to_add.append(f"<would-create:{label_name}>")
        else:
            fallback = buckets["other"]["label"]
            if fallback and not dry_run:
                labels_to_add.append(get_or_create_label(fallback, mailbox=mailbox))
    elif bucket_cfg.get("label"):
        if not dry_run:
            labels_to_add.append(get_or_create_label(bucket_cfg["label"], mailbox=mailbox))
        else:
            labels_to_add.append(f"<would-create:{bucket_cfg['label']}>")

    # If a sub_label_by_sender map exists on the bucket, apply the matching sub-label too.
    # Used by Joseph's company_bills bucket → ADP / Acrisure / Berkshire / etc sub-labels.
    sub_map = bucket_cfg.get("sub_label_by_sender_contains") or {}
    if sub_map:
        from_addr = (classification.get("_from") or "").lower()
        for needle, sub_label in sub_map.items():
            if needle.lower() in from_addr:
                if not dry_run:
                    labels_to_add.append(get_or_create_label(sub_label, mailbox=mailbox))
                else:
                    labels_to_add.append(f"<would-create:{sub_label}>")
                break

    # Any bucket: if project_hint resolves to a known project, also apply project label
    if classification.get("project_hint"):
        xp = registry.find_project(classification["project_hint"])
        if xp:
            xp_name = registry.project_label_name(xp)
            if not dry_run:
                labels_to_add.append(get_or_create_label(xp_name, mailbox=mailbox))
            else:
                labels_to_add.append(f"<would-create:{xp_name}>")

    skip_inbox = bucket_cfg.get("skip_inbox", False)
    if skip_inbox:
        labels_to_remove.append("INBOX")

    quiet_categories = rules.get("quiet_categories") or ["bid_invite", "vendor", "promo"]
    if category not in quiet_categories:
        labels_to_add.append("IMPORTANT")

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
            "mailbox": mailbox,
        }

    try:
        apply_labels(message_id, labels_to_add, labels_to_remove or None, mailbox=mailbox)
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
        "mailbox": mailbox,
    }
