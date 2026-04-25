"""
mine_006_emails.py — Export all inbox + sent emails from allenenriquez006@gmail.com.
Extracts contacts + context for AI automation lead identification.

Output: .tmp/email_leads_006.json

Usage:
    python3 tools/shared/mine_006_emails.py
    python3 tools/shared/mine_006_emails.py --max 500  # limit messages per label
"""

import argparse
import base64
import json
import pickle
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
TOKEN_PATH = BASE_DIR / "projects" / "personal" / "token_personal.pickle"
OUT_PATH = BASE_DIR / ".tmp" / "email_leads_006.json"


def get_service():
    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return build("gmail", "v1", credentials=creds)


def decode_body(payload):
    """Extract plain text from message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = decode_body(part)
        if text:
            return text
    return ""


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def parse_email_address(raw):
    """Extract name + email from 'Name <email>' or just 'email'."""
    match = re.match(r"^(.*?)\s*<([^>]+)>$", raw.strip())
    if match:
        return match.group(1).strip().strip('"'), match.group(2).strip().lower()
    raw = raw.strip().lower()
    return "", raw


def list_message_ids(service, label, max_results):
    ids = []
    page_token = None
    while True:
        kwargs = {"userId": "me", "labelIds": [label], "maxResults": min(500, max_results - len(ids))}
        if page_token:
            kwargs["pageToken"] = page_token
        res = service.users().messages().list(**kwargs).execute()
        ids.extend(m["id"] for m in res.get("messages", []))
        page_token = res.get("nextPageToken")
        if not page_token or len(ids) >= max_results:
            break
    return ids


def fetch_messages_batch(service, ids, batch_size=50):
    """Fetch message metadata + snippet in batches."""
    messages = []
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        for msg_id in batch:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Cc", "Subject", "Date"],
                ).execute()
                messages.append(msg)
            except Exception as e:
                print(f"  Skip {msg_id}: {e}", file=sys.stderr)
        print(f"  Fetched {min(i + batch_size, len(ids))}/{len(ids)}...", file=sys.stderr)
        time.sleep(0.1)
    return messages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=2000, help="Max messages per label (inbox + sent)")
    args = parser.parse_args()

    service = get_service()
    print("Connected to Gmail API", file=sys.stderr)

    contacts = defaultdict(lambda: {
        "name": "",
        "email": "",
        "directions": [],   # "received" | "sent"
        "subjects": [],
        "snippets": [],
        "dates": [],
        "thread_count": 0,
    })

    for label, direction in [("INBOX", "received"), ("SENT", "sent")]:
        print(f"\nFetching {label} (up to {args.max})...", file=sys.stderr)
        ids = list_message_ids(service, label, args.max)
        print(f"  {len(ids)} messages found", file=sys.stderr)
        messages = fetch_messages_batch(service, ids)

        for msg in messages:
            headers = msg.get("payload", {}).get("headers", [])
            snippet = msg.get("snippet", "")
            subject = get_header(headers, "Subject")
            date = get_header(headers, "Date")

            if direction == "received":
                raw_from = get_header(headers, "From")
                name, email = parse_email_address(raw_from)
                if not email or "noreply" in email or "no-reply" in email or "mailer" in email:
                    continue
                key = email
                if name and not contacts[key]["name"]:
                    contacts[key]["name"] = name
            else:
                # sent — collect all To + Cc recipients
                raw_to = get_header(headers, "To") + ", " + get_header(headers, "Cc")
                recipients = [r.strip() for r in raw_to.split(",") if r.strip()]
                for raw in recipients:
                    name, email = parse_email_address(raw)
                    if not email or "noreply" in email or "no-reply" in email:
                        continue
                    key = email
                    if name and not contacts[key]["name"]:
                        contacts[key]["name"] = name
                    if direction not in contacts[key]["directions"]:
                        contacts[key]["directions"].append(direction)
                    if subject and subject not in contacts[key]["subjects"]:
                        contacts[key]["subjects"].append(subject)
                    if snippet and len(contacts[key]["snippets"]) < 5:
                        contacts[key]["snippets"].append(snippet[:200])
                    if date:
                        contacts[key]["dates"].append(date)
                    contacts[key]["email"] = key
                    contacts[key]["thread_count"] += 1
                continue

            key = email
            if direction not in contacts[key]["directions"]:
                contacts[key]["directions"].append(direction)
            if subject and subject not in contacts[key]["subjects"]:
                contacts[key]["subjects"].append(subject)
            if snippet and len(contacts[key]["snippets"]) < 5:
                contacts[key]["snippets"].append(snippet[:200])
            if date:
                contacts[key]["dates"].append(date)
            contacts[key]["email"] = key
            contacts[key]["thread_count"] += 1

    # Sort by thread count desc, filter noise
    SKIP_DOMAINS = {
        "gmail.com", "google.com", "facebook.com", "linkedin.com", "twitter.com",
        "instagram.com", "youtube.com", "apple.com", "microsoft.com", "amazon.com",
        "notion.so", "slack.com", "zoom.us", "dropbox.com", "paypal.com",
        "stripe.com", "shopify.com", "mailchimp.com", "hubspot.com", "salesforce.com",
        "indeed.com", "seek.com.au", "upwork.com", "fiverr.com",
    }

    # Keep gmail only if they had bidirectional contact (both sent + received)
    results = []
    for email, data in contacts.items():
        domain = email.split("@")[-1] if "@" in email else ""
        is_noise_domain = domain in SKIP_DOMAINS
        is_bidirectional = len(set(data["directions"])) > 1

        if is_noise_domain and not is_bidirectional:
            continue
        if not email or "@" not in email:
            continue

        data["email"] = email
        data["domain"] = domain
        data["bidirectional"] = is_bidirectional
        # Keep most recent 3 subjects + 3 snippets
        data["subjects"] = data["subjects"][:5]
        data["snippets"] = data["snippets"][:3]
        data["dates"] = sorted(set(data["dates"]))[-3:]
        results.append(data)

    results.sort(key=lambda x: (x["bidirectional"], x["thread_count"]), reverse=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump({"total_contacts": len(results), "contacts": results}, f, indent=2)

    print(f"\nDone. {len(results)} contacts → {OUT_PATH}", file=sys.stderr)
    print(f"Run: python3 tools/shared/analyze_email_leads.py to score leads")


if __name__ == "__main__":
    main()
