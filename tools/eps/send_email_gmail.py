"""
Send an email via Gmail API using the EPS Google account.

Replaces send_email_pipedrive.py — Pipedrive's API does not support sending.
Emails sent here auto-sync to Pipedrive if the Gmail inbox is connected.

Usage:
    python3 tools/send_email_gmail.py \
        --to "client@example.com" \
        --subject "Your Quote" \
        --body "Hi Allen, ..." \
        [--deal-id "1076"]

Requires in projects/eps/.env:
    PIPEDRIVE_FROM_EMAIL   (Gmail address to send from, e.g. sales@epsolution.com.au)
    GMAIL_FROM_NAME        (display name, e.g. "Allen @ EPS")

Requires EPS token with gmail.send scope:
    python3 tools/auth_eps.py
"""

import argparse
import base64
import os
import pickle
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'eps' / 'token_eps.pickle'
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'

load_dotenv(ENV_FILE)

FROM_EMAIL = os.getenv('PIPEDRIVE_FROM_EMAIL', '')
FROM_NAME = os.getenv('GMAIL_FROM_NAME', 'EPS Painting & Cleaning')


def get_creds():
    if not TOKEN_FILE.exists():
        print("ERROR: EPS token not found. Run: python3 tools/auth_eps.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if 'https://www.googleapis.com/auth/gmail.send' not in (creds.scopes or []):
        print("ERROR: Gmail send scope not authorised. Run: python3 tools/auth_eps.py", file=sys.stderr)
        sys.exit(1)
    return creds


def send_email(to_email, subject, body, deal_id=None, html=False, attachment_path=None):
    if not FROM_EMAIL:
        print("ERROR: PIPEDRIVE_FROM_EMAIL not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)

    creds = get_creds()
    service = build('gmail', 'v1', credentials=creds)

    # Always use multipart/mixed when attaching a file so body + attachment coexist
    if attachment_path:
        msg = MIMEMultipart('mixed')
        msg['to'] = to_email
        msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['subject'] = subject
        body_part = MIMEText(body, 'html' if html else 'plain')
        msg.attach(body_part)
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = Path(attachment_path).name
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(part)
    elif html:
        msg = MIMEMultipart('alternative')
        msg['to'] = to_email
        msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['subject'] = subject
        msg.attach(MIMEText(body, 'html'))
    else:
        msg = MIMEText(body, 'plain')
        msg['to'] = to_email
        msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['subject'] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--to',      required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--body',    required=True)
    parser.add_argument('--deal-id', default='', dest='deal_id')
    args = parser.parse_args()

    result = send_email(args.to, args.subject, args.body, args.deal_id)
    print(f"Sent: {args.subject}")
    print(f"To: {args.to}")
    print(f"Message ID: {result.get('id')}")
    if args.deal_id:
        print(f"Note: will auto-sync to Pipedrive deal #{args.deal_id} if inbox is connected")


if __name__ == '__main__':
    main()
