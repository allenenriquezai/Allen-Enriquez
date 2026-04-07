"""
One-time OAuth setup for the EPS Google account.

Run this once to authorise the EPS Google account. It will open a browser window
for you to log in, then save the token to projects/eps/token_eps.pickle.

Usage:
    python3 tools/auth_eps.py

After running, all EPS Google tools will use the EPS account automatically.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'credentials_eps.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.send',
]


def main():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.valid:
        print("EPS token is already valid. No action needed.")
        return

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("EPS token refreshed.")
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        print("EPS account authorised.")

    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)

    print(f"Token saved to: {TOKEN_FILE}")


if __name__ == '__main__':
    main()
