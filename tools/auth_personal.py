"""
One-time OAuth setup for the personal Google account.

Prerequisites:
1. Go to Google Cloud Console (console.cloud.google.com)
2. Select your project (or create one)
3. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
4. Application type: Desktop app
5. Download the JSON → save as: projects/personal/credentials_personal.json

Then run:
    python3 tools/auth_personal.py

After running, Gmail and Calendar for your personal account will be accessible.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'projects', 'personal', 'credentials_personal.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'personal', 'token_personal.pickle')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: credentials file not found at {CREDENTIALS_FILE}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        return

    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.valid and set(SCOPES).issubset(creds.scopes or []):
        print("Personal token is already valid with all required scopes.")
        return

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("Personal token refreshed.")
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        print("Personal account authorised.")

    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)

    print(f"Token saved to: {TOKEN_FILE}")


if __name__ == '__main__':
    main()
