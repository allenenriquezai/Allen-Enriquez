"""One-time cleanup: move misclassified emails out of 2. Team/Daily Accomplishments PH.

Rules (deterministic, no AI calls):
  - From ryan@ or joseph@ → remove team_daily, add 6. Office
  - From Kharene/Kim but subject doesn't match daily report pattern
    → remove team_daily, add 5. Archive/Review

Usage:
    python3 fix_team_daily.py            # dry-run
    python3 fix_team_daily.py --execute  # apply
"""
from __future__ import annotations
import argparse
import re
import time

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config


TEAM_DAILY_LABEL = "2. Team/Daily Accomplishments PH"
OFFICE_LABEL = "6. Office"
REVIEW_LABEL = "5. Archive/Review"

DAILY_SUBJECT_RE = re.compile(r"daily accomplishment|attendance.*accomplishment", re.IGNORECASE)

RYAN_JOSEPH = ["ryan@sc-incorporated.com", "joseph@sc-incorporated.com"]
KHARENE_KIM = ["kharene@sc-incorporated.com", "kim.bayudan.stoneworkcontracting@gmail.com"]


def get_svc():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_or_find_label(svc, name: str, all_labels: list[dict]) -> str:
    for l in all_labels:
        if l["name"] == name:
            return l["id"]
    created = svc.users().labels().create(userId="me", body={
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }).execute()
    all_labels.append({"id": created["id"], "name": name})
    return created["id"]


def run(dry_run: bool = True) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n=== fix_team_daily — {mode} ===\n")

    svc = get_svc()
    all_labels = svc.users().labels().list(userId="me").execute().get("labels", [])

    td_label = next((l for l in all_labels if l["name"] == TEAM_DAILY_LABEL), None)
    if not td_label:
        print("team_daily label not found — nothing to do.")
        return

    # Paginate all messages in team_daily
    ids = []
    page_token = None
    while True:
        kwargs = {"userId": "me", "labelIds": [td_label["id"]], "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.users().messages().list(**kwargs).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Total in team_daily: {len(ids)}\n")

    to_office = []
    to_review = []
    keep = []

    for mid in ids:
        m = svc.users().messages().get(userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject"]).execute()
        h = {x["name"].lower(): x["value"] for x in m.get("payload", {}).get("headers", [])}
        frm = h.get("from", "").lower()
        subj = h.get("subject", "")

        from_ryan_joseph = any(s in frm for s in RYAN_JOSEPH)
        from_kharene_kim = any(s in frm for s in KHARENE_KIM)
        is_daily_subject = bool(DAILY_SUBJECT_RE.search(subj))

        if from_ryan_joseph:
            to_office.append((mid, frm, subj))
        elif from_kharene_kim and not is_daily_subject:
            to_review.append((mid, frm, subj))
        else:
            keep.append((mid, frm, subj))

    print(f"→ Move to Office ({len(to_office)}):")
    for _, frm, subj in to_office:
        print(f"  [{frm[:45]}] {subj[:70]}")

    print(f"\n→ Move to Archive/Review ({len(to_review)}):")
    for _, frm, subj in to_review:
        print(f"  [{frm[:45]}] {subj[:70]}")

    print(f"\n→ Keep in Daily Accomplishments ({len(keep)})")

    if dry_run:
        print("\nDry run complete. Run with --execute to apply.")
        return

    office_id = get_or_find_label(svc, OFFICE_LABEL, all_labels)
    review_id = get_or_find_label(svc, REVIEW_LABEL, all_labels)
    td_id = td_label["id"]

    moved = 0
    for mid, _, _ in to_office + to_review:
        add_id = office_id if (mid, _, _) in [(x[0], x[1], x[2]) for x in to_office] else review_id
        # Determine correct target
        target_id = office_id if any(mid == x[0] for x in to_office) else review_id
        try:
            svc.users().messages().modify(userId="me", id=mid,
                body={"addLabelIds": [target_id], "removeLabelIds": [td_id]}).execute()
            moved += 1
        except HttpError as e:
            print(f"  WARNING: {mid} failed: {e}")
        time.sleep(0.05)

    print(f"\nDone. Moved {moved} emails.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.execute)
