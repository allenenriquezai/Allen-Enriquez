"""
Send, draft, or preview an email via personal Gmail API.

Two accounts supported:
  --from 006  → allenenriquez.ai@gmail.com (token_personal_ai.pickle)
  --from ai   → allenenriquez.ai@gmail.com (token_personal_ai.pickle) [DEFAULT]

Usage:
    # Draft (safest — saves to Drafts folder, doesn't send)
    python3 tools/send_personal_email.py --draft \\
        --to "ryan@sc-incorporated.com" \\
        --subject "Ryan — few things" \\
        --body-file "projects/personal/.tmp/clients/ryan/discovery-email-body.md" \\
        --attach "projects/personal/.tmp/clients/ryan/gmail-mockup.png"

    # Send (after reviewing the draft in Gmail)
    python3 tools/send_personal_email.py --send --to ... --subject ... --body-file ...

    # Dry run (prints, does nothing)
    python3 tools/send_personal_email.py --dry-run --to ... --subject ... --body ...

Accounts:
  Default from account: ai. Override with --from 006 if you still need the old one.
"""

import argparse
import base64
import json
import mimetypes
import pickle
import sys
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent

ACCOUNTS = {
    'ai': {
        'token': BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle',
        'email': 'allenenriquez.ai@gmail.com',
        'name': 'Allen Enriquez',
        'auth_hint': 'python3 tools/auth_personal_ai.py',
    },
    '006': {
        'token': BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle',
        'email': 'allenenriquez.ai@gmail.com',
        'name': 'Allen Enriquez',
        'auth_hint': 'python3 tools/auth_personal.py',
    },
}


def get_creds(account):
    cfg = ACCOUNTS[account]
    if not cfg['token'].exists():
        print(f"ERROR: Token missing for account '{account}' at {cfg['token']}", file=sys.stderr)
        print(f"Run: {cfg['auth_hint']}", file=sys.stderr)
        sys.exit(1)
    with open(cfg['token'], 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(cfg['token'], 'wb') as f:
            pickle.dump(creds, f)
    return creds


def build_message(to_email, subject, body, from_name, from_email, attachments):
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, 'plain'))
        for path in attachments:
            p = Path(path)
            if not p.exists():
                print(f"WARNING: attachment not found: {p}", file=sys.stderr)
                continue
            mime_type, _ = mimetypes.guess_type(str(p))
            maintype, subtype = (mime_type or 'application/octet-stream').split('/', 1)
            with open(p, 'rb') as f:
                part = MIMEBase(maintype, subtype)
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{p.name}"')
            msg.attach(part)
    else:
        msg = MIMEText(body, 'plain')

    msg['to'] = to_email
    msg['from'] = f"{from_name} <{from_email}>"
    msg['subject'] = subject
    return msg


def action(mode, account, to_email, subject, body, attachments, dry_run):
    cfg = ACCOUNTS[account]
    msg = build_message(to_email, subject, body, cfg['name'], cfg['email'], attachments)

    if dry_run:
        print(f"--- DRY RUN ---")
        print(f"Mode: {mode}")
        print(f"Account: {account} ({cfg['email']})")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Attachments: {attachments or 'none'}")
        print(f"\nBody preview ({len(body)} chars):")
        print(body[:500] + ('...[truncated]' if len(body) > 500 else ''))
        print("--- END ---")
        return {"status": "dry_run", "mode": mode, "to": to_email, "subject": subject}

    creds = get_creds(account)
    service = build('gmail', 'v1', credentials=creds)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    if mode == 'draft':
        result = service.users().drafts().create(
            userId='me', body={'message': {'raw': raw}}
        ).execute()
        return {
            "status": "drafted",
            "to": to_email,
            "subject": subject,
            "draft_id": result.get('id'),
            "message_id": result.get('message', {}).get('id'),
        }
    elif mode == 'send':
        result = service.users().messages().send(
            userId='me', body={'raw': raw}
        ).execute()
        return {"status": "sent", "to": to_email, "subject": subject, "message_id": result.get('id')}
    else:
        raise ValueError(f"Unknown mode: {mode}")


def main():
    parser = argparse.ArgumentParser(description="Draft or send an email via personal Gmail")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--draft', action='store_const', const='draft', dest='mode',
                      help='Save to Drafts folder (safest)')
    mode.add_argument('--send', action='store_const', const='send', dest='mode',
                      help='Send immediately')
    mode.add_argument('--dry-run', action='store_true', dest='dry_run',
                      help='Print preview, do nothing')

    parser.add_argument('--from', dest='account', choices=['ai', '006'], default='ai',
                        help='Which account to use (default: ai)')
    parser.add_argument('--to', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--body', default=None)
    parser.add_argument('--body-file', default=None, dest='body_file')
    parser.add_argument('--attach', action='append', default=[],
                        help='Attachment path (repeatable)')
    args = parser.parse_args()

    if args.body_file:
        body = Path(args.body_file).read_text().strip()
    elif args.body:
        body = args.body
    else:
        print("ERROR: Provide --body or --body-file", file=sys.stderr)
        sys.exit(1)

    mode = args.mode if args.mode else None
    if args.dry_run:
        mode = 'draft'  # any valid mode, action() branches on dry_run first

    result = action(mode, args.account, args.to, args.subject, body, args.attach, args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
