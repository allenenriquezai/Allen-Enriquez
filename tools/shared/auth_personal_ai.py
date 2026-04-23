"""
One-time OAuth setup for the allenenriquez.ai@gmail.com account.

Uses the Enriquez OS GCP project (credentials_enriquez_os.json) — the same
project that hosts Ryan's audit client. The .ai account must be added as a
test user on the OAuth consent screen.

Run once:
    python3 tools/auth_personal_ai.py

After that, tools/send_personal_email.py --from ai works.
"""

import os
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / 'projects' / 'personal' / 'credentials_enriquez_os.json'
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]


def main():
    if not CREDENTIALS_FILE.exists():
        print(f"ERROR: credentials file not found at {CREDENTIALS_FILE}")
        return

    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.valid and set(SCOPES).issubset(creds.scopes or []):
        print(".ai account token valid with all scopes.")
        return

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(".ai token refreshed.")
        except Exception as e:
            print(f"Refresh failed ({e}) — running fresh OAuth flow.")
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        print("\nBrowser will open. Log in as allenenriquez.ai@gmail.com")
        print("You'll see the 'Google hasn't verified this app' warning — that's expected.")
        print("Click Advanced → Go to Allen Enriquez (unsafe) → Continue.\n")
        creds = flow.run_local_server(port=0)
        print(".ai account authorised.")

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)
    print(f"Token saved: {TOKEN_FILE}")


if __name__ == '__main__':
    main()
