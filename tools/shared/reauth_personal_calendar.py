"""
reauth_personal_calendar.py — Re-auth personal Google token with calendar write scope.
Run once interactively: python3 tools/shared/reauth_personal_calendar.py
Browser will open for Google consent. Token saved back to token_personal.pickle.
"""

import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_PATH = Path(__file__).parent.parent.parent / "projects/personal/credentials_personal.json"
TOKEN_PATH = Path(__file__).parent.parent.parent / "projects/personal/token_personal.pickle"

if not CREDS_PATH.exists():
    raise FileNotFoundError(f"credentials file not found: {CREDS_PATH}")

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_PATH, "wb") as f:
    pickle.dump(creds, f)

print(f"Token saved to {TOKEN_PATH}")
print("Scopes:", creds.scopes)

# Verify calendar access
service = build("calendar", "v3", credentials=creds)
cal = service.calendars().get(calendarId="primary").execute()
print(f"Calendar access confirmed: {cal.get('summary')}")
