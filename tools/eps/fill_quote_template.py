"""
Fills an EPS quote Google Doc with data from quote_data.json.

Handles:
  - Text placeholder replacement (square bracket format)
  - Line items table row insertion + cell filling

Usage:
    python3 tools/fill_quote_template.py --doc-id "DOC_ID" --data "projects/eps/.tmp/quote_data.json"

Placeholders in the template:
    [organizationName]                          → company_name (or blank)
    [personName]                                → client
    [projectAddress]                            → address
    [jobDescription]                            → job description bullets
    [Subtotal]                                  → subtotal
    [GST]                                       → GST
    [Total]                                     → total
    [Deal ID (deal id)]                         → deal_id (or blank)
    [Short today's date (datetime today_short)] → quote_date
    [personEmail]                               → email (or blank)
"""

import argparse
import json
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def replace_text(docs, doc_id, replacements):
    """Batch replace all [placeholder] tags in the document."""
    requests = []
    for placeholder, value in replacements.items():
        requests.append({
            'replaceAllText': {
                'containsText': {'text': placeholder, 'matchCase': True},
                'replaceText': value
            }
        })
    if requests:
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()


def center_quote_title(docs, doc_id, title):
    """Find the quote title paragraph in the doc and apply center alignment."""
    doc = docs.documents().get(documentId=doc_id).execute()
    for element in doc.get('body', {}).get('content', []):
        if 'paragraph' not in element:
            continue
        text = ''.join(
            el.get('textRun', {}).get('content', '')
            for el in element['paragraph'].get('elements', [])
        ).strip()
        if text == title:
            docs.documents().batchUpdate(documentId=doc_id, body={'requests': [{
                'updateParagraphStyle': {
                    'range': {'startIndex': element['startIndex'], 'endIndex': element['endIndex']},
                    'paragraphStyle': {'alignment': 'CENTER'},
                    'fields': 'alignment'
                }
            }]}).execute()
            break


def find_line_items_table(doc):
    """Find the first table in the document that has 5 columns (line items table)."""
    for el in doc.get('body', {}).get('content', []):
        if 'table' in el:
            table = el['table']
            if table.get('columns', 0) == 5:
                return el
    return None


def fill_line_items_table(docs, doc_id, line_items):
    """Insert rows into the line items table and fill with data."""
    # Step 1: read doc, find table
    doc = docs.documents().get(documentId=doc_id).execute()
    table_el = find_line_items_table(doc)
    if not table_el:
        print("WARNING: line items table not found in document.", file=sys.stderr)
        return

    table_start = table_el['startIndex']

    # Step 2: insert additional rows if needed (row 0 = header, row 1 = 1 empty row already exists)
    rows_to_insert = len(line_items) - 1
    if rows_to_insert > 0:
        requests = []
        for i in range(rows_to_insert):
            requests.append({
                'insertTableRow': {
                    'tableCellLocation': {
                        'tableStartLocation': {'index': table_start},
                        'rowIndex': 1,
                        'columnIndex': 0
                    },
                    'insertBelow': True
                }
            })
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

    # Step 3: re-read doc to get updated cell indices
    doc = docs.documents().get(documentId=doc_id).execute()
    table_el = find_line_items_table(doc)
    table = table_el['table']

    # Step 4: build insertText requests for all data rows (reverse order to preserve indices)
    insert_requests = []

    for row_idx, item in enumerate(line_items):
        actual_row = row_idx + 1  # skip header row (row 0)
        cells = table['tableRows'][actual_row]['tableCells']

        qty = item.get('quantity', item.get('area_sqm', ''))
        qty_str = str(int(qty)) if isinstance(qty, float) and qty.is_integer() else str(qty)

        cell_values = [
            item.get('code', ''),
            item.get('description', ''),
            qty_str,
            f"${item['rate']:,.2f}",
            f"${item['subtotal']:,.2f}",
        ]

        for col_idx, value in enumerate(cell_values):
            if not value:
                continue
            start_index = cells[col_idx]['content'][0]['startIndex']
            insert_requests.append({
                'insertText': {
                    'location': {'index': start_index},
                    'text': str(value)
                }
            })

    # Process in reverse index order so earlier insertions don't shift later indices
    insert_requests.sort(key=lambda r: r['insertText']['location']['index'], reverse=True)

    if insert_requests:
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': insert_requests}).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc-id', required=True, help='Google Doc ID')
    parser.add_argument('--data',   required=True, help='Path to quote_data.json')
    args = parser.parse_args()

    data_path = os.path.join(BASE_DIR, args.data) if not os.path.isabs(args.data) else args.data
    with open(data_path) as f:
        data = json.load(f)

    # Save doc_id into quote_data.json so update_quote_doc.py can find the doc later
    if 'doc_id' not in data or data.get('doc_id') != args.doc_id:
        data['doc_id'] = args.doc_id
        with open(data_path, 'w') as f:
            json.dump(data, f, indent=2)

    job_desc = "\n\n".join(data.get('job_description', []))

    replacements = {
        '[organizationName]':                          data.get('company_name', ''),
        '[personName]':                                data.get('client', ''),
        '[projectAddress]':                            data.get('address', ''),
        '[jobDescription]':                            job_desc,
        '[Subtotal]':                                  f"${data.get('subtotal', 0):,.2f}",
        '[GST]':                                       f"${data.get('gst', 0):,.2f}",
        '[Total]':                                     f"${data.get('total', 0):,.2f}",
        "[Deal ID (deal id)]":                         str(data.get('deal_id', '')),
        "[Short today's date (datetime today_short)]": data.get('quote_date', ''),
        '[personEmail]':                               data.get('email', ''),
    }

    creds = get_creds()
    docs = build('docs', 'v1', credentials=creds)

    # Fill text placeholders first
    replace_text(docs, args.doc_id, replacements)

    # Center the quote title if present
    if data.get('quote_title'):
        center_quote_title(docs, args.doc_id, data['quote_title'])

    # Fill line items table
    fill_line_items_table(docs, args.doc_id, data.get('line_items', []))

    print(f"Done. https://docs.google.com/document/d/{args.doc_id}/edit")


if __name__ == '__main__':
    main()
