import os
import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = '/Users/allenenriquez/Desktop/SystemA/token.pickle'
SPREADSHEET_ID = '1Upp2lhiTeRsybaBHEy5_6FTBLcCN5fJ8l-TjpyqrGUs'

def get_creds():
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def main():
    creds = get_creds()
    sheets = build('sheets', 'v4', credentials=creds)

    # Updated headers including new columns
    headers = [[
        'Business Name', 'Owner Name', 'Phone', 'Email', 'Website',
        'City', 'Service Areas', 'Rating', 'Reviews',
        'Owner LinkedIn', 'Facebook Page', 'Notes'
    ]]

    data = [
        [
            "Glenny's Painting",
            'Carlos A. Glenny',
            '(980) 322-5043',
            'carlos.glenny@glennyspainting.com',
            'glennyspaintingandremodeling.com',
            'Charlotte, NC',
            'Charlotte area',
            '',
            '45 (Yelp)',
            '',
            'https://www.facebook.com/GlennysPainting/',
            'Father and son duo. Est. 2010. Interior/exterior, cabinet painting, drywall repair.'
        ],
        [
            'Brothers Painting JJ, LLC',
            'Julio C. Martinez',
            '(704) 837-9811',
            '',
            'brotherspaintingnc.com',
            'Charlotte, NC',
            'Charlotte area',
            '',
            '',
            '',
            'https://www.facebook.com/p/Brothers-Painting-JJ-LLC-100081562010782/',
            'Owner-operated since 1997. Interior/exterior, cabinet refinishing, drywall, popcorn removal.'
        ],
        [
            'Century Painting',
            'Jack Jordan',
            '(704) 245-9409',
            'j***@centurypaintingnc.com',
            'centurypaintingnc.com',
            'Charlotte, NC',
            'Charlotte Metro',
            '4.8',
            '',
            'https://www.linkedin.com/company/century-painting-nc',
            'https://www.facebook.com/Centurypaintingnc/',
            'Est. 1999. Owner Jack Jordan started career in 1994. Residential and commercial.'
        ],
        [
            'Ukie Painting',
            'Vitalii Skochenko',
            '(980) 447-6311',
            '',
            'ukiepainting.com',
            'Mint Hill, NC',
            'Charlotte, Matthews, Mint Hill, Ballantyne, Harrisburg',
            '',
            '',
            '',
            'https://www.facebook.com/UkiePainting/',
            'Est. 2020. Locally owned. Residential interior/exterior. 10-19 employees.'
        ],
        [
            'SouthEnd Painting Contractors',
            'Todd Cahill',
            '(704) 522-0000',
            '',
            'southendpainting.com',
            'Charlotte, NC',
            'Charlotte, NC',
            '',
            '',
            '',
            'https://www.facebook.com/Charlottesbestpaintingcompany/',
            'Est. 2000. BBB accredited, Angie\'s List A-rated. Residential and commercial, roofing.'
        ],
    ]

    all_rows = headers + data

    # Clear and rewrite sheet
    sheets.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1'
    ).execute()

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A1',
        valueInputOption='RAW',
        body={'values': all_rows}
    ).execute()

    # Bold + freeze header row
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
        spreadsheetId=SPREADSHEET_ID,
        body={'requests': requests}
    ).execute()

    print("Done! 5 painting companies written to the sheet.")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

if __name__ == '__main__':
    main()
