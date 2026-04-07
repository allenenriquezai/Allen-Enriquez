"""
Updates the job description section of a filled EPS quote Google Doc.

Uses the 'jobDescription' Named Range to locate and replace the content —
no find/replace needed, works regardless of what text is currently in the doc.

Usage:
    python3 tools/update_quote_doc.py --doc-id "DOC_ID" --data "projects/eps/.tmp/quote_data.json"

The doc must have a Named Range called 'jobDescription'. This is added automatically
when the doc is created from the EPS quote template (as of 2026-04-07).
"""

import argparse
import json
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')


def get_creds():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: EPS token not found. Run: python3 tools/auth_eps.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_named_range(doc, name):
    """Return (startIndex, endIndex) for a named range, or None if not found."""
    named_ranges = doc.get('namedRanges', {})
    if name not in named_ranges:
        return None
    named_range_list = named_ranges[name]['namedRanges']
    if not named_range_list:
        return None
    r = named_range_list[0]['ranges'][0]
    return r['startIndex'], r['endIndex']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc-id', required=True, help='Google Doc ID to update')
    parser.add_argument('--data',   required=True, help='Path to quote_data.json')
    args = parser.parse_args()

    data_path = os.path.join(BASE_DIR, args.data) if not os.path.isabs(args.data) else args.data
    with open(data_path) as f:
        data = json.load(f)

    new_text = "\n".join(data.get('job_description', []))

    creds = get_creds()
    docs = build('docs', 'v1', credentials=creds)

    doc = docs.documents().get(documentId=args.doc_id).execute()
    result = get_named_range(doc, 'jobDescription')

    if not result:
        print("ERROR: 'jobDescription' named range not found in doc.", file=sys.stderr)
        print("This doc was created before named range support was added.", file=sys.stderr)
        print("Run: python3 tools/add_named_range_to_doc.py --doc-id DOC_ID", file=sys.stderr)
        sys.exit(1)

    start, end = result

    # Collect all text run ranges within the named range (in reverse order to preserve indices)
    text_runs = []
    for el in doc['body']['content']:
        if 'table' not in el:
            continue
        for row in el['table']['tableRows']:
            for cell in row['tableCells']:
                for para in cell['content']:
                    if 'paragraph' not in para:
                        continue
                    for pe in para['paragraph']['elements']:
                        if 'textRun' not in pe:
                            continue
                        s = pe['startIndex']
                        e = pe['endIndex']
                        # Only include runs fully within the named range
                        if s >= start and e <= end:
                            # Don't delete paragraph-end markers (\n at end of cell/para)
                            content = pe['textRun']['content']
                            if content.endswith('\n'):
                                e -= 1  # exclude the \n
                            if s < e:
                                text_runs.append((s, e))

    # Sort in reverse order so deletions don't shift earlier indices
    text_runs.sort(key=lambda x: x[0], reverse=True)

    requests = []

    # Delete each text run's content
    for s, e in text_runs:
        requests.append({
            'deleteContentRange': {
                'range': {'startIndex': s, 'endIndex': e}
            }
        })

    # After all deletions the named range startIndex points to the first \n (now empty paragraphs)
    # Insert new text at start — goes in before the first empty paragraph marker
    requests.append({
        'insertText': {
            'location': {'index': start},
            'text': new_text
        }
    })

    docs.documents().batchUpdate(documentId=args.doc_id, body={'requests': requests}).execute()

    print(f"Done. https://docs.google.com/document/d/{args.doc_id}/edit")


if __name__ == '__main__':
    main()
