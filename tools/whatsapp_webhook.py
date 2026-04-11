"""
WhatsApp webhook server — receives incoming messages via Meta Cloud API.

Messages are saved to projects/eps/.tmp/whatsapp_inbox.json (append-only).

Usage:
    # Start the server (default port 5001)
    python3 tools/whatsapp_webhook.py

    # Read inbox
    python3 tools/whatsapp_webhook.py --read

    # Read inbox (unread only)
    python3 tools/whatsapp_webhook.py --unread

    # Mark all as read
    python3 tools/whatsapp_webhook.py --mark-read

Then run ngrok in another terminal:
    ~/bin/ngrok http 5001

Configure the ngrok HTTPS URL as the webhook in Meta Developer Portal.

Webhook verify token: eps-whatsapp-verify-2026
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"
INBOX_FILE = BASE_DIR / "projects" / "eps" / ".tmp" / "whatsapp_inbox.json"

load_dotenv(ENV_FILE)

VERIFY_TOKEN = "eps-whatsapp-verify-2026"

app = Flask(__name__)


def _load_inbox() -> list:
    if INBOX_FILE.exists():
        with open(INBOX_FILE, "r") as f:
            return json.load(f)
    return []


def _save_inbox(messages: list):
    INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INBOX_FILE, "w") as f:
        json.dump(messages, f, indent=2)


@app.route("/webhook", methods=["GET"])
def verify():
    """Meta webhook verification (GET request)."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"Webhook verified.")
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive():
    """Receive incoming WhatsApp messages."""
    data = request.get_json()

    if not data:
        return "OK", 200

    messages = _load_inbox()

    # Extract messages from the webhook payload
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Get contact info
            contacts = {c["wa_id"]: c.get("profile", {}).get("name", "Unknown")
                        for c in value.get("contacts", [])}

            for msg in value.get("messages", []):
                sender = msg.get("from", "")
                msg_type = msg.get("type", "")

                # Extract message content based on type
                if msg_type == "text":
                    content = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    content = "[Image] " + msg.get("image", {}).get("caption", "")
                elif msg_type == "document":
                    content = "[Document] " + msg.get("document", {}).get("filename", "")
                elif msg_type == "audio":
                    content = "[Audio message]"
                elif msg_type == "video":
                    content = "[Video] " + msg.get("video", {}).get("caption", "")
                elif msg_type == "location":
                    loc = msg.get("location", {})
                    content = f"[Location] {loc.get('latitude')}, {loc.get('longitude')}"
                elif msg_type == "reaction":
                    content = f"[Reaction] {msg.get('reaction', {}).get('emoji', '')}"
                else:
                    content = f"[{msg_type}]"

                record = {
                    "id": msg.get("id", ""),
                    "from": sender,
                    "name": contacts.get(sender, "Unknown"),
                    "type": msg_type,
                    "content": content,
                    "timestamp": msg.get("timestamp", ""),
                    "received_at": datetime.now().isoformat(),
                    "read": False,
                }

                messages.append(record)
                print(f"[{record['received_at']}] {record['name']} ({sender}): {content}")

    _save_inbox(messages)
    return "OK", 200


def print_inbox(unread_only=False):
    messages = _load_inbox()
    if unread_only:
        messages = [m for m in messages if not m.get("read")]

    if not messages:
        print("No messages." if not unread_only else "No unread messages.")
        return

    for m in messages:
        status = " " if m.get("read") else "*"
        ts = m.get("received_at", "")[:19]
        print(f"  {status} [{ts}] {m['name']} ({m['from']}): {m['content']}")
    print(f"\nTotal: {len(messages)}")


def mark_all_read():
    messages = _load_inbox()
    for m in messages:
        m["read"] = True
    _save_inbox(messages)
    print(f"Marked {len(messages)} messages as read.")


def main():
    parser = argparse.ArgumentParser(description="WhatsApp webhook server")
    parser.add_argument("--read", action="store_true", help="Read all messages")
    parser.add_argument("--unread", action="store_true", help="Read unread messages only")
    parser.add_argument("--mark-read", action="store_true", help="Mark all as read")
    parser.add_argument("--port", type=int, default=5001, help="Server port (default: 5001)")
    args = parser.parse_args()

    if args.read:
        print_inbox(unread_only=False)
    elif args.unread:
        print_inbox(unread_only=True)
    elif args.mark_read:
        mark_all_read()
    else:
        print(f"Starting WhatsApp webhook server on port {args.port}...")
        print(f"Verify token: {VERIFY_TOKEN}")
        print(f"Inbox file: {INBOX_FILE}")
        print(f"\nRun ngrok in another terminal:")
        print(f"  ~/bin/ngrok http {args.port}")
        print(f"\nThen configure webhook URL in Meta Developer Portal:")
        print(f"  https://<ngrok-url>/webhook")
        app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
