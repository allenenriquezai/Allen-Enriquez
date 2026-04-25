"""
Export an EPS quote Google Doc to PDF.

Usage:
    python3 tools/export_quote_pdf.py --doc-id DOC_ID

Output: projects/eps/.tmp/quote_output.pdf
"""

import argparse
import os
import pickle
import sys

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')
OUTPUT     = os.path.join(BASE_DIR, 'projects', 'eps', '.tmp', 'quote_output.pdf')


def get_creds():
    if not os.path.exists(TOKEN_FILE):
        sys.exit("ERROR: Run python3 tools/auth_eps.py first")
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc-id', required=True, help='Google Doc ID')
    parser.add_argument('--output', default=OUTPUT, help='Output PDF path')
    args = parser.parse_args()

    creds = get_creds()
    drive = build('drive', 'v3', credentials=creds)

    pdf_bytes = drive.files().export(
        fileId=args.doc_id,
        mimeType='application/pdf'
    ).execute()

    out_path = args.output
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(pdf_bytes)

    print(f"PDF saved: {out_path}")
    print(f"Doc: https://docs.google.com/document/d/{args.doc_id}/edit")


if __name__ == '__main__':
    main()
