"""
WhatsApp Business API tool — send messages, check messages, manage templates.

Uses Meta Cloud API (graph.facebook.com).

Usage:
    # Send a text message
    python3 tools/whatsapp.py send --to "61412345678" --message "Hi there"

    # Send a template message (required for first contact / 24hr window expired)
    python3 tools/whatsapp.py send-template --to "61412345678" --template "hello_world"

    # List message templates
    python3 tools/whatsapp.py templates

    # Get business profile
    python3 tools/whatsapp.py profile

Requires in projects/eps/.env:
    WHATSAPP_ACCESS_TOKEN
    WHATSAPP_PHONE_NUMBER_ID
    WHATSAPP_BUSINESS_ACCOUNT_ID
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"

load_dotenv(ENV_FILE)

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")

API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def _headers():
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _check_creds():
    if not ACCESS_TOKEN:
        print("ERROR: WHATSAPP_ACCESS_TOKEN not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)
    if not PHONE_NUMBER_ID:
        print("ERROR: WHATSAPP_PHONE_NUMBER_ID not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)


def _format_phone(phone: str) -> str:
    """Strip spaces, dashes, plus signs — API wants digits only."""
    return phone.replace(" ", "").replace("-", "").replace("+", "")


def send_message(to: str, message: str) -> dict:
    """Send a text message. Only works within 24hr conversation window."""
    _check_creds()
    to = _format_phone(to)
    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    resp = requests.post(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def send_template(to: str, template: str, language: str = "en_US", components: list = None) -> dict:
    """Send a template message. Use this for first contact or after 24hr window."""
    _check_creds()
    to = _format_phone(to)
    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": language},
        },
    }
    if components:
        payload["template"]["components"] = components
    resp = requests.post(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def list_templates() -> list:
    """List all approved message templates."""
    _check_creds()
    url = f"{BASE_URL}/{BUSINESS_ACCOUNT_ID}/message_templates"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def get_profile() -> dict:
    """Get the WhatsApp Business profile."""
    _check_creds()
    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/whatsapp_business_profile"
    params = {"fields": "about,address,description,email,profile_picture_url,websites,vertical"}
    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def get_phone_info() -> dict:
    """Get info about the registered phone number."""
    _check_creds()
    url = f"{BASE_URL}/{PHONE_NUMBER_ID}"
    params = {"fields": "display_phone_number,verified_name,quality_rating,platform_type"}
    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Business API tool")
    sub = parser.add_subparsers(dest="command")

    # send
    p_send = sub.add_parser("send", help="Send a text message")
    p_send.add_argument("--to", required=True, help="Phone number with country code (e.g. 61412345678)")
    p_send.add_argument("--message", required=True, help="Message text")

    # send-template
    p_tmpl = sub.add_parser("send-template", help="Send a template message")
    p_tmpl.add_argument("--to", required=True, help="Phone number with country code")
    p_tmpl.add_argument("--template", required=True, help="Template name")
    p_tmpl.add_argument("--language", default="en_US", help="Language code (default: en_US)")

    # templates
    sub.add_parser("templates", help="List message templates")

    # profile
    sub.add_parser("profile", help="Get business profile")

    # phone
    sub.add_parser("phone", help="Get phone number info")

    args = parser.parse_args()

    if args.command == "send":
        result = send_message(args.to, args.message)
        print(json.dumps(result, indent=2))

    elif args.command == "send-template":
        result = send_template(args.to, args.template, args.language)
        print(json.dumps(result, indent=2))

    elif args.command == "templates":
        templates = list_templates()
        if not templates:
            print("No templates found.")
        for t in templates:
            status = t.get("status", "unknown")
            print(f"  {t['name']} ({t.get('language', '?')}) — {status}")

    elif args.command == "profile":
        result = get_profile()
        print(json.dumps(result, indent=2))

    elif args.command == "phone":
        result = get_phone_info()
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
