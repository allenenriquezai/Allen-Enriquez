"""Fix known mislabeled emails in Ryan's inbox. Saves rollback state before every change.

Modes:
  team-fix      Move 7 misclassified Team/Daily emails to correct buckets.
  review-reclass  Re-classify 334 Archive/Review emails through the full service classifier.
  rollback FILE   Revert all changes recorded in a rollback JSON file.

Usage:
    python3 tools/ryan_fix_labels.py --mode team-fix --dry-run
    python3 tools/ryan_fix_labels.py --mode team-fix

    python3 tools/ryan_fix_labels.py --mode review-reclass --dry-run
    python3 tools/ryan_fix_labels.py --mode review-reclass

    python3 tools/ryan_fix_labels.py --rollback projects/personal/clients/ryan/rollback_team_fix.json
    python3 tools/ryan_fix_labels.py --rollback projects/personal/clients/ryan/rollback_review_reclass.json
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = REPO_ROOT / "projects/personal/clients/ryan"
SERVICE_DIR = REPO_ROOT / "services/ryan-labeler"
TOKEN_FILE = CLIENT_DIR / "token_ryan.pickle"

TEAM_LABEL_NAME = "2. Team/Daily Accomplishments PH"
REVIEW_LABEL_NAME = "5. Archive/Review"
COLONY_PARC_LABEL_NAME = "1. Projects/Colony Parc II"


# ─── Gmail auth ─────────────────────────────────────────────────────────────

def get_service():
    if not TOKEN_FILE.exists():
        sys.exit(f"Token not found: {TOKEN_FILE}")
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ─── Gmail helpers ──────────────────────────────────────────────────────────

def get_label_id(service, name: str) -> str | None:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for l in labels:
        if l["name"] == name:
            return l["id"]
    return None


def list_label_messages(service, label_id: str, max_results: int = 500) -> list[str]:
    ids, page_token = [], None
    while len(ids) < max_results:
        resp = service.users().messages().list(
            userId="me", labelIds=[label_id],
            maxResults=min(500, max_results - len(ids)),
            pageToken=page_token,
        ).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def fetch_meta(service, message_id: str) -> dict:
    m = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["From", "Subject"],
    ).execute()
    h = {hh["name"].lower(): hh["value"] for hh in m.get("payload", {}).get("headers", [])}
    return {
        "id": m["id"],
        "label_ids": m.get("labelIds", []),
        "from": h.get("from", ""),
        "subject": h.get("subject", ""),
        "snippet": m.get("snippet", ""),
    }


def modify_message(service, message_id: str, add_ids: list[str], remove_ids: list[str],
                   dry_run: bool) -> bool:
    if dry_run:
        return True
    body: dict = {}
    if add_ids:
        body["addLabelIds"] = add_ids
    if remove_ids:
        body["removeLabelIds"] = remove_ids
    for attempt in range(3):
        try:
            service.users().messages().modify(userId="me", id=message_id, body=body).execute()
            return True
        except HttpError as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(2 ** attempt + 1)
            else:
                print(f"  ERROR {message_id}: {e}", file=sys.stderr)
                return False
    return False


# ─── Rollback helpers ────────────────────────────────────────────────────────

def save_rollback(path: Path, entries: list[dict]) -> None:
    """Each entry: {message_id, original_label_ids, applied_add, applied_remove}"""
    path.write_text(json.dumps({"saved_at": datetime.now(timezone.utc).isoformat(),
                                "entries": entries}, indent=2))
    print(f"Rollback saved: {path}")


def do_rollback(rollback_path: Path, dry_run: bool) -> None:
    if not rollback_path.exists():
        sys.exit(f"Rollback file not found: {rollback_path}")
    data = json.loads(rollback_path.read_text())
    entries = data["entries"]
    print(f"Rolling back {len(entries)} messages (saved {data['saved_at']})")
    service = get_service()
    ok = err = 0
    for e in entries:
        mid = e["message_id"]
        orig = set(e["original_label_ids"])
        # Undo our changes: remove what we added, restore what we removed
        undo_add = e.get("applied_remove", [])   # we removed these → add back
        undo_remove = e.get("applied_add", [])   # we added these → remove
        if dry_run:
            print(f"  [dry] {mid}: restore {undo_add}, remove {undo_remove}")
            ok += 1
            continue
        success = modify_message(service, mid, undo_add, undo_remove, dry_run=False)
        if success:
            ok += 1
        else:
            err += 1
        time.sleep(0.1)
    print(f"Rollback done: {ok} ok, {err} errors")


# ─── Mode: team-fix ─────────────────────────────────────────────────────────

def run_team_fix(dry_run: bool) -> None:
    """Fix 7 misclassified Team/Daily emails."""
    service = get_service()
    label_ids = {l["name"]: l["id"] for l in
                 service.users().labels().list(userId="me").execute().get("labels", [])}

    team_lid = label_ids.get(TEAM_LABEL_NAME)
    if not team_lid:
        sys.exit(f"Label not found: {TEAM_LABEL_NAME}")

    colony_lid = label_ids.get(COLONY_PARC_LABEL_NAME)
    if not colony_lid and not dry_run:
        # Create it if missing
        created = service.users().labels().create(
            userId="me", body={"name": COLONY_PARC_LABEL_NAME,
                               "labelListVisibility": "labelShow",
                               "messageListVisibility": "show"}
        ).execute()
        colony_lid = created["id"]
        print(f"Created label: {COLONY_PARC_LABEL_NAME}")

    print(f"Listing messages in {TEAM_LABEL_NAME}...")
    ids = list_label_messages(service, team_lid)
    print(f"Found {len(ids)} messages. Scanning for misclassified...")

    rollback_entries = []
    autodesk_fixed = 0
    hiring_fixed = 0

    for mid in ids:
        msg = fetch_meta(service, mid)
        from_lower = msg["from"].lower()
        subject_lower = msg["subject"].lower()

        is_autodesk = "autodesk" in from_lower or "acc.autodesk.com" in from_lower
        is_hiring = "now hiring" in subject_lower

        if not is_autodesk and not is_hiring:
            continue

        orig_labels = msg["label_ids"]

        if is_autodesk:
            # Move to Colony Parc II project, remove team label
            add_ids = [colony_lid] if colony_lid else []
            remove_ids = [team_lid]
            action = f"→ {COLONY_PARC_LABEL_NAME}"
            autodesk_fixed += 1
        else:  # is_hiring
            # Remove team label; admin_ops has no Gmail label (stays in inbox)
            add_ids = []
            remove_ids = [team_lid]
            action = "→ (admin_ops, no label) removed from Team"
            hiring_fixed += 1

        if dry_run:
            print(f"  [dry] {action}")
            print(f"    From   : {msg['from'][:80]}")
            print(f"    Subject: {msg['subject'][:80]}")
        else:
            success = modify_message(service, mid, add_ids, remove_ids, dry_run=False)
            if success:
                rollback_entries.append({
                    "message_id": mid,
                    "original_label_ids": orig_labels,
                    "applied_add": add_ids,
                    "applied_remove": remove_ids,
                })
            time.sleep(0.1)

    print(f"\nTeam-fix complete: {autodesk_fixed} Autodesk → Colony Parc II, "
          f"{hiring_fixed} hiring → admin_ops")

    if not dry_run and rollback_entries:
        save_rollback(CLIENT_DIR / "rollback_team_fix.json", rollback_entries)


# ─── Mode: review-reclass ───────────────────────────────────────────────────

def run_review_reclass(dry_run: bool) -> None:
    """Re-classify all Archive/Review emails through the full service classifier."""
    os.environ["CONFIG_DIR"] = str(CLIENT_DIR)
    sys.path.insert(0, str(SERVICE_DIR))

    import config as svc_config  # noqa
    import classifier as svc_classifier  # noqa
    import labeler as svc_labeler  # noqa

    service = get_service()
    label_ids_map = {l["name"]: l["id"] for l in
                     service.users().labels().list(userId="me").execute().get("labels", [])}

    review_lid = label_ids_map.get(REVIEW_LABEL_NAME)
    if not review_lid:
        sys.exit(f"Label not found: {REVIEW_LABEL_NAME}")

    print(f"Listing messages in {REVIEW_LABEL_NAME}...")
    ids = list_label_messages(service, review_lid, max_results=500)
    print(f"Found {len(ids)} messages. Re-classifying with full classifier...\n")

    rollback_entries = []
    by_bucket: dict[str, int] = {}
    errors = 0

    for i, mid in enumerate(ids, 1):
        msg = fetch_meta(service, mid)
        from_addr = msg["from"]
        subject = msg["subject"]
        snippet = msg["snippet"]
        orig_labels = msg["label_ids"]

        try:
            cls = svc_classifier.classify(from_addr, subject, snippet)
        except Exception as e:
            print(f"  classify error {mid}: {e}", file=sys.stderr)
            errors += 1
            continue

        category = cls["category"]
        by_bucket[category] = by_bucket.get(category, 0) + 1

        if category == "other":
            # Still can't classify — leave it in Archive/Review
            if i % 50 == 0:
                print(f"  {i}/{len(ids)} ...")
            continue

        # Apply correct label via full routing logic
        try:
            result = svc_labeler.route_and_label(mid, cls, dry_run=dry_run)
        except Exception as e:
            print(f"  routing error {mid}: {e}", file=sys.stderr)
            errors += 1
            continue

        if dry_run:
            if category != "other":
                print(f"  [dry] {category} (conf={cls['confidence']:.2f})")
                print(f"    From   : {from_addr[:80]}")
                print(f"    Subject: {subject[:80]}")
                print(f"    Would add: {result.get('would_add', [])}")
                print()
        else:
            # Also remove Archive/Review label now that it's properly classified
            if result.get("applied"):
                modify_message(service, mid, [], [review_lid], dry_run=False)
                rollback_entries.append({
                    "message_id": mid,
                    "original_label_ids": orig_labels,
                    "applied_add": result.get("labels_added", []),
                    "applied_remove": [review_lid],
                })
            time.sleep(0.15)

        if i % 25 == 0:
            print(f"  {i}/{len(ids)} — buckets so far: {by_bucket}")

    print(f"\nReview re-class complete:")
    print(f"  Total: {len(ids)}, Errors: {errors}")
    print(f"  By bucket: {by_bucket}")

    if not dry_run and rollback_entries:
        save_rollback(CLIENT_DIR / "rollback_review_reclass.json", rollback_entries)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["team-fix", "review-reclass"],
                    help="Which fix to run")
    ap.add_argument("--rollback", type=Path, default=None,
                    help="Path to rollback JSON to revert a previous run")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview only, no Gmail writes")
    args = ap.parse_args()

    if args.rollback:
        do_rollback(args.rollback, dry_run=args.dry_run)
    elif args.mode == "team-fix":
        run_team_fix(dry_run=args.dry_run)
    elif args.mode == "review-reclass":
        run_review_reclass(dry_run=args.dry_run)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
