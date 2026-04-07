"""
One-time script: adds the 'jobDescription' Named Range to a quote doc that
was created before named range support was added to the template.

Finds the job description table cell by scanning all table cells for the
largest text block (heuristic: job desc is always the longest cell).

Usage:
    python3 tools/add_named_range_to_doc.py --doc-id "DOC_ID"
"""

import argparse
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')


def get_creds():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: EPS token not found.", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def find_job_desc_cell(doc):
    """
    Scan all table cells. Return (startIndex, endIndex) of the cell whose
    text content is the longest — that's the job description cell.
    """
    best = None
    best_len = 0

    for el in doc['body']['content']:
        if 'table' not in el:
            continue
        for row in el['table']['tableRows']:
            for cell in row['tableCells']:
                cell_text = ''
                cell_start = None
                cell_end = None
                for para in cell['content']:
                    if 'paragraph' not in para:
                        continue
                    for pe in para['paragraph']['elements']:
                        if 'textRun' not in pe:
                            continue
                        t = pe['textRun']['content']
                        cell_text += t
                        if cell_start is None:
                            cell_start = pe['startIndex']
                        cell_end = pe['endIndex']
                if cell_start is not None and len(cell_text.strip()) > best_len:
                    best_len = len(cell_text.strip())
                    best = (cell_start, cell_end)

    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc-id', required=True)
    args = parser.parse_args()

    creds = get_creds()
    docs = build('docs', 'v1', credentials=creds)

    doc = docs.documents().get(documentId=args.doc_id).execute()

    # Check if named range already exists
    if 'jobDescription' in doc.get('namedRanges', {}):
        print("Named range 'jobDescription' already exists. Nothing to do.")
        return

    result = find_job_desc_cell(doc)
    if not result:
        print("ERROR: Could not find job description cell.", file=sys.stderr)
        sys.exit(1)

    start, end = result
    print(f"Found job description at indices {start}–{end}")

    docs.documents().batchUpdate(documentId=args.doc_id, body={'requests': [{
        'createNamedRange': {
            'name': 'jobDescription',
            'range': {'startIndex': start, 'endIndex': end}
        }
    }]}).execute()

    print(f"Named range 'jobDescription' added to doc.")
    print(f"Now run: python3 tools/update_quote_doc.py --doc-id {args.doc_id} --data projects/eps/.tmp/quote_data.json")


if __name__ == '__main__':
    main()
