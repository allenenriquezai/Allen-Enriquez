import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

CREDS_FILE = '/Users/allenenriquez/Desktop/SystemA/credentials.json'
TOKEN_FILE = '/Users/allenenriquez/Desktop/SystemA/token.pickle'

def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def main():
    creds = authenticate()
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)

    # Create SystemA folder in Drive
    folder_meta = {
        'name': 'SystemA',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive.files().create(body=folder_meta, fields='id,name').execute()
    folder_id = folder['id']
    print(f"Created folder: SystemA (id: {folder_id})")

    # Create Google Sheet inside the folder
    sheet_meta = {
        'name': 'Charlotte NC Prospects',
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id]
    }
    sheet_file = drive.files().create(body=sheet_meta, fields='id,name,webViewLink').execute()
    spreadsheet_id = sheet_file['id']
    print(f"Created sheet: Charlotte NC Prospects (id: {spreadsheet_id})")
    print(f"URL: {sheet_file['webViewLink']}")

    # Write headers
    headers = [[
        'Business Name', 'Phone', 'City', 'Website',
        'Owner Name', 'Service Areas', 'Rating', 'Reviews', 'Notes'
    ]]
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Sheet1!A1',
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()

    # Bold + freeze the header row
    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold"
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"
            }
        }
    ]
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()

    print("\nDone! Sheet is ready with headers.")
    print(f"Open it here: {sheet_file['webViewLink']}")

if __name__ == '__main__':
    main()
