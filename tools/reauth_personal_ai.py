"""
One-time re-auth for allenenriquez.ai@gmail.com personal token.
Uses credentials_personal.json (personal-brand-492708, Sheets API enabled).

Run: python3 tools/reauth_personal_ai.py
Sign in as allenenriquez.ai@gmail.com when browser opens.
"""
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.readonly',
]

BASE_DIR = Path(__file__).parent.parent
CREDS_FILE = BASE_DIR / 'projects' / 'personal' / 'credentials_personal.json'
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, 'wb') as f:
    pickle.dump(creds, f)

print(f"Done. Token saved: {TOKEN_FILE}")
