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

    new_rows = [
        [
            'Providence Paint Company',
            'Jerry Kressner',
            '(704) 521-1250',
            'jerry@providencepaint.com',
            'providencepaint.com',
            'Charlotte, NC',
            'Charlotte area',
            '',
            '',
            'https://www.linkedin.com/company/providence-paint',
            'https://www.facebook.com/providencepaintcompany/',
            'Est. 1997. Owner-operated. Residential and commercial painting.'
        ],
        [
            'Advance Painting Contractors',
            'Mitchell Fogel / Luis Arroyo',
            '(704) 266-3365',
            'office@GoWithAdvance.com',
            'advancecontractorsnc.com',
            'Charlotte, NC',
            'Greater Charlotte area',
            '',
            '',
            '',
            'https://www.facebook.com/GoWithAdvance/',
            'Est. 2004. Two managing partners. Residential and commercial. 18+ years in business.'
        ],
        [
            'Charlotte Pro Painters',
            'Adam Mashal',
            '(704) 313-8452',
            '',
            'charlottepropainters.com',
            'Charlotte, NC',
            'Charlotte, NC & surrounding areas',
            '',
            '10',
            '',
            'https://www.facebook.com/CharlotteProPainters/',
            'Locally owned. Residential and commercial. Fully insured with 2-year warranty.'
        ],
        [
            'All Star Painting',
            'Michael Hook',
            '',
            '',
            'allstarpaintingclt.com',
            'Charlotte, NC',
            'Charlotte, NC & surrounding areas',
            '',
            '',
            '',
            'https://www.facebook.com/allstarpaintingclt/',
            'Owner Michael Hook, Charlotte native since 1997. BBB accredited since 2020. Residential focus.'
        ],
        [
            'The Holy Painter',
            '',
            '(980) 258-4148',
            '',
            'theholypaintercharlotte.com',
            'Charlotte, NC',
            'Charlotte, SouthPark, Indian Trail',
            '',
            '',
            '',
            'https://www.facebook.com/p/The-Holy-Painter-100083347178910/',
            'Family-owned, 29 years experience. Interior/exterior, cabinet painting. 10-year workmanship guarantee on exterior.'
        ],
    ]

    # Append rows after existing data
    sheets.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': new_rows}
    ).execute()

    print(f"Done! 5 more companies added to the sheet.")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

if __name__ == '__main__':
    main()
