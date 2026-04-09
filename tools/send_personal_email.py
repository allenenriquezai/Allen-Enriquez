"""
Send an email via personal Gmail API.

Usage:
    python3 tools/send_personal_email.py \
        --to "prospect@example.com" \
        --subject "Quick follow-up" \
        --body "Hi Chris, ..."

    python3 tools/send_personal_email.py \
        --to "prospect@example.com" \
        --subject "Quick follow-up" \
        --body-file "projects/personal/.tmp/email_draft.txt"

Requires: projects/personal/token_personal.pickle (run auth_personal.py first)
"""

import argparse
import base64
import json
import pickle
import sys
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'
FROM_EMAIL = 'allenenriquez006@gmail.com'
FROM_NAME = 'Allen Enriquez'


def get_creds():
    if not TOKEN_FILE.exists():
        print("ERROR: Personal token not found. Run: python3 tools/auth_personal.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def send_email(to_email, subject, body, dry_run=False):
    msg = MIMEText(body, 'plain')
    msg['to'] = to_email
    msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['subject'] = subject

    if dry_run:
        print(f"--- DRY RUN ---\nTo: {to_email}\nFrom: {FROM_NAME} <{FROM_EMAIL}>\nSubject: {subject}\n\n{body}\n--- END ---")
        return {"status": "dry_run", "to": to_email, "subject": subject}

    creds = get_creds()
    service = build('gmail', 'v1', credentials=creds)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return {"status": "sent", "to": to_email, "subject": subject, "message_id": result.get('id')}


def main():
    parser = argparse.ArgumentParser(description="Send email via personal Gmail")
    parser.add_argument('--to', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--body', default=None)
    parser.add_argument('--body-file', default=None, dest='body_file')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run')
    args = parser.parse_args()

    if args.body_file:
        body = Path(args.body_file).read_text().strip()
    elif args.body:
        body = args.body
    else:
        print("ERROR: Provide --body or --body-file", file=sys.stderr)
        sys.exit(1)

    result = send_email(args.to, args.subject, body, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
