"""
One-time setup: create the "PH Outreach" Google Sheet with schema.

Usage:
    python3 tools/setup_ph_outreach_sheet.py

After run, copy the printed spreadsheet_id into
projects/personal/reference/outreach_config.yaml (spreadsheet_id: "...").
"""

import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'

SHEET_TITLE = "PH Outreach"

COLUMNS = [
    "Date Added", "Name", "Company", "Platform", "Profile URL",
    "Website", "Email", "Phone", "FB URL", "IG URL",
    "Segment", "Tier", "Personal Hook",
    "Status",
    "Touch 1 Date", "Touch 1 Channel", "Touch 1 Msg",
    "Touch 2 Date", "Touch 2 Channel", "Touch 2 Msg",
    "Touch 3 Date", "Touch 3 Channel", "Touch 3 Msg",
    "Last Reply Date", "Last Reply", "Next Action",
    "Source", "Notes",
]


def get_creds():
    if not TOKEN_FILE.exists():
        print(f"ERROR: Personal token not found at {TOKEN_FILE}", file=sys.stderr)
        print("Run: python3 tools/auth_personal.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def main():
    creds = get_creds()
    sheets = build('sheets', 'v4', credentials=creds)

    new_sheet = {
        'properties': {'title': SHEET_TITLE},
        'sheets': [{'properties': {'title': 'Prospects', 'sheetId': 0}}],
    }
    created = sheets.spreadsheets().create(body=new_sheet, fields='spreadsheetId').execute()
    sid = created['spreadsheetId']
    print(f"Created spreadsheet: {sid}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sid}/edit")

    sheets.spreadsheets().values().update(
        spreadsheetId=sid,
        range='Prospects!A1',
        valueInputOption='RAW',
        body={'values': [COLUMNS]},
    ).execute()

    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0},
                }},
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=sid, body={'requests': requests}
    ).execute()

    print("\n=== NEXT STEP ===")
    print(f"Edit projects/personal/reference/outreach_config.yaml")
    print(f'Set: spreadsheet_id: "{sid}"')


if __name__ == '__main__':
    main()
