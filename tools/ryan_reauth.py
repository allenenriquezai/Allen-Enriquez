"""
One-time OAuth re-authentication for Ryan Canton (ryan@sc-incorporated.com).

Upgrades Ryan's existing readonly token at
projects/personal/clients/ryan/token_ryan.pickle to the expanded scopes needed
for the Gmail labeler + morning briefer:

    - gmail.readonly
    - gmail.modify
    - gmail.labels
    - calendar.readonly

Uses the Enriquez OS GCP project (credentials_enriquez_os.json). Ryan must be
added as a test user on the OAuth consent screen.

Because the browser consent flow has to happen as Ryan (not Allen), this script
supports three modes:

    1. --mode url-only (default)
       Print the authorization URL + a short Allen-to-Ryan template message.
       Ryan opens the URL, signs in, clicks through the "unverified app"
       warning, and sends the one-time code back to Allen.

         python3 tools/ryan_reauth.py

    2. --mode exchange --code <code>
       After Ryan sends the code, Allen exchanges it for a token and writes
       the pickle.

         python3 tools/ryan_reauth.py --mode exchange --code 4/0A...

    3. --mode local
       Full auth_personal_ai.py-style flow: opens a browser on THIS machine
       and runs a local redirect server. Use when Allen and Ryan are on a
       shared screen (screen share, in-person).

         python3 tools/ryan_reauth.py --mode local

Note on OOB deprecation:
    Google has been phasing out the urn:ietf:wg:oauth:2.0:oob redirect. If
    the url-only / exchange flow errors ("invalid_request" or similar),
    fall back to --mode local on a shared screen, OR have Ryan clone this
    repo and run --mode local locally, then send Allen the resulting pickle.
"""

import argparse
import base64
import pickle
import sys
from pathlib import Path

from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / 'projects' / 'personal' / 'credentials_enriquez_os.json'
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'clients' / 'ryan' / 'token_ryan.pickle'

OOB_REDIRECT = 'urn:ietf:wg:oauth:2.0:oob'

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _save_and_report(creds):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)

    granted = set(creds.scopes or [])
    missing = [s for s in SCOPES if s not in granted]

    print("\n=== Token saved ===")
    print(f"Path:    {TOKEN_FILE}")
    print(f"Expiry:  {creds.expiry}")
    print("Scopes:")
    for s in creds.scopes or []:
        print(f"  - {s}")

    if missing:
        print("\nWARNING: missing expected scopes:")
        for s in missing:
            print(f"  - {s}")
        print("Ryan may have unticked a permission on the consent screen.")
    else:
        print("\nAll expected scopes granted.")

    print("\n=== Upload to Secret Manager ===")
    print("Run this to push the new pickle to Secret Manager (Cloud Run reads it):")
    print(f"  base64 < {TOKEN_FILE} | gcloud secrets versions add RYAN_GMAIL_TOKEN --data-file=-")
    print("\nFor reference, here is the base64 payload (first 80 chars):")
    encoded = base64.b64encode(TOKEN_FILE.read_bytes()).decode()
    print(f"  {encoded[:80]}...  ({len(encoded)} chars total)")


def mode_url_only():
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES, redirect_uri=OOB_REDIRECT
    )
    auth_url, _ = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent'
    )

    print("=== Ryan re-auth: URL-only mode ===\n")
    print("1. Send Ryan this message (WhatsApp / email / Slack):\n")
    print("---8<--- copy below this line ---8<---")
    print("Hey Ryan — quick one, I need to upgrade the Gmail connection so")
    print("the auto-labeler + morning brief can actually sort and draft.")
    print("Open this link, sign in with ryan@sc-incorporated.com, click")
    print("through the 'Google hasn't verified this app' warning")
    print("(Advanced -> Continue), tick all boxes, and send me the code")
    print("Google shows you on the final screen.\n")
    print(auth_url)
    print("--->8--- copy above this line --->8---\n")
    print("2. Ryan's final screen shows a one-time code.")
    print("   Redirect URI used: " + OOB_REDIRECT)
    print("3. When Ryan sends you the code, run:")
    print("     python3 tools/ryan_reauth.py --mode exchange --code <CODE>")


def mode_exchange(code: str):
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES, redirect_uri=OOB_REDIRECT
    )
    flow.fetch_token(code=code)
    _save_and_report(flow.credentials)


def mode_local():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    print("\nBrowser will open. Sign in as ryan@sc-incorporated.com.")
    print("You'll see the 'Google hasn't verified this app' warning — that's expected.")
    print("Click Advanced -> Go to Allen Enriquez (unsafe) -> Continue. Tick all boxes.\n")
    creds = flow.run_local_server(port=0)
    _save_and_report(creds)


def main():
    parser = argparse.ArgumentParser(description="OAuth re-auth for Ryan Canton.")
    parser.add_argument('--mode', choices=['url-only', 'exchange', 'local'],
                        default='url-only')
    parser.add_argument('--code', help="One-time code from Ryan (exchange mode only).")
    args = parser.parse_args()

    if not CREDENTIALS_FILE.exists():
        print(f"ERROR: credentials file not found at {CREDENTIALS_FILE}")
        sys.exit(1)

    if args.mode == 'url-only':
        mode_url_only()
    elif args.mode == 'exchange':
        if not args.code:
            print("ERROR: --mode exchange requires --code <code>")
            sys.exit(2)
        mode_exchange(args.code)
    elif args.mode == 'local':
        mode_local()


if __name__ == '__main__':
    main()
