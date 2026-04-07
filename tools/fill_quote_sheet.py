"""
Fill a copied EPS Paint quote sheet with data from quote_data.json.

Usage:
    python3 tools/fill_quote_sheet.py --sheet SHEET_ID [--deal-id ID] [--person NAME]

Args:
    --sheet     Google Sheets ID of the copied (not template) quote sheet
    --deal-id   Pipedrive deal ID for [dealID] placeholder (optional)
    --person    Contact person name for [personName] placeholder (optional)

Input:  projects/eps/.tmp/quote_data.json  (output of calculate_quote.py)
Output: Fills the sheet in-place

Template A4 frame: rows 138–166
    Row 138:      Header
    Row 139:      Gap
    Rows 140–165: Working space (26 rows) — items, spacer, totals written here
    Row 166:      Blue divider (fixed)

Fill behaviour:
    - Clear B140:F165 first
    - Write N items starting at row 140
    - Spacer at row 140+N (empty)
    - Totals at rows 140+N+1, 140+N+2, 140+N+3
    - Rows after totals stay blank within the frame
    - If N > 22: insert extra rows at 162 to keep blue divider below totals
"""

import argparse
import json
import os
import pickle
import sys

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')
DATA_FILE  = os.path.join(BASE_DIR, 'projects', 'eps', '.tmp', 'quote_data.json')

# ── Colours ────────────────────────────────────────────────────────────────────
def rgb(r, g, b): return {'red': r/255, 'green': g/255, 'blue': b/255}
EPS_BLUE = rgb(26, 60, 140)
BLACK    = rgb(0, 0, 0)
LGRAY    = rgb(220, 220, 220)

# ── Sheet constants ─────────────────────────────────────────────────────────────
SID          = 0
LI_START_ROW = 140   # 1-indexed, always fixed — first line item row

# Column indices (0-based): A=0 B=1 C=2 D=3 E=4 F=5 G=6
A, B, C, D, E, F, G = range(7)

CURRENCY = {'type': 'CURRENCY', 'pattern': '$#,##0.00'}


# ── Helpers ─────────────────────────────────────────────────────────────────────
def get_creds():
    if not os.path.exists(TOKEN_FILE):
        sys.exit("ERROR: Run python3 tools/auth_eps.py first")
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def gr(r1, r2, c1, c2):
    """GridRange — 0-indexed, end-exclusive."""
    return {'sheetId': SID,
            'startRowIndex': r1, 'endRowIndex': r2,
            'startColumnIndex': c1, 'endColumnIndex': c2}


def solid(color, width=1):
    return {'style': 'SOLID', 'width': width, 'color': color}


def make_cell(value=None, bold=False, font_size=10, fg=None, bg=None,
              halign='LEFT', wrap=False, num_fmt=None):
    fmt = {
        'textFormat': {
            'bold': bold,
            'fontSize': font_size,
            'foregroundColor': fg or BLACK,
            'fontFamily': 'Arial',
        },
        'horizontalAlignment': halign,
        'verticalAlignment': 'MIDDLE',
        'wrapStrategy': 'WRAP' if wrap else 'OVERFLOW_CELL',
    }
    if bg:
        fmt['backgroundColor'] = bg
    if num_fmt:
        fmt['numberFormat'] = num_fmt

    cd = {'userEnteredFormat': fmt}
    if value is not None:
        if isinstance(value, str) and value.startswith('='):
            cd['userEnteredValue'] = {'formulaValue': value}
        elif isinstance(value, (int, float)):
            cd['userEnteredValue'] = {'numberValue': value}
        else:
            cd['userEnteredValue'] = {'stringValue': str(value)}
    return cd


EC = {'userEnteredValue': {'stringValue': ''}, 'userEnteredFormat': {}}


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sheet',    required=True, help='Google Sheets ID to fill')
    parser.add_argument('--deal-id',  default='',    help='Pipedrive deal ID')
    parser.add_argument('--person',   default='',    help='Contact person name')
    args = parser.parse_args()

    # ── Load data ──────────────────────────────────────────────────────────────
    if not os.path.exists(DATA_FILE):
        sys.exit(f"ERROR: {DATA_FILE} not found. Run calculate_quote.py first.")

    with open(DATA_FILE) as f:
        data = json.load(f)

    line_items = data.get('line_items', [])
    if not line_items:
        sys.exit("ERROR: No line_items in quote_data.json")

    N = len(line_items)

    # Working space: rows 140–165 = 26 rows. Need N items + 1 spacer + 3 totals.
    # Max items without inserting: 26 - 4 = 22
    TEMPLATE_SLOTS = 22
    extra_rows     = max(0, N - TEMPLATE_SLOTS)

    last_item_row = LI_START_ROW + N - 1
    spacer_row    = LI_START_ROW + N
    sub_row       = LI_START_ROW + N + 1
    gst_row       = LI_START_ROW + N + 2
    tot_row       = LI_START_ROW + N + 3

    # ── Auth ───────────────────────────────────────────────────────────────────
    creds  = get_creds()
    sheets = build('sheets', 'v4', credentials=creds)

    ss_id = args.sheet
    reqs  = []

    # ── 1. Fill text placeholders ──────────────────────────────────────────────
    job_desc = data.get('job_description', '')
    if isinstance(job_desc, list):
        job_desc = '\n'.join(job_desc)

    placeholders = {
        '[dealID]':           args.deal_id or '',
        '[shortTodaysDate]':  data.get('quote_date', ''),
        '[organizationName]': data.get('client', ''),
        '[personName]':       args.person or '',
        '[projectAddress]':   data.get('address', ''),
        '[jobDescription]':   job_desc,
    }

    for find, replace in placeholders.items():
        reqs.append({'findReplace': {
            'find':        find,
            'replacement': replace,
            'allSheets':   True,
        }})

    # ── 2. Clear working space B140:F165 ───────────────────────────────────────
    sheets.spreadsheets().values().clear(
        spreadsheetId=ss_id,
        range='B140:F165'
    ).execute()

    # ── 3. Insert extra rows if N > 22 ─────────────────────────────────────────
    # Insert at row 162 (0-idx 161) — just before where spacer would sit,
    # keeping the blue divider below the totals
    if extra_rows > 0:
        reqs.append({'insertDimension': {
            'range': {'sheetId': SID, 'dimension': 'ROWS',
                      'startIndex': 161, 'endIndex': 161 + extra_rows},
            'inheritFromBefore': True,
        }})
        reqs.append({'updateDimensionProperties': {
            'range': {'sheetId': SID, 'dimension': 'ROWS',
                      'startIndex': 161, 'endIndex': 161 + extra_rows},
            'properties': {'pixelSize': 34}, 'fields': 'pixelSize'
        }})

    # ── 4. Write line items (rows 140 … 140+N-1) ───────────────────────────────
    li_rows = []
    for i, item in enumerate(line_items):
        r   = LI_START_ROW + i
        qty = item.get('quantity', item.get('qty', 0))
        li_rows.append({'values': [
            EC,
            make_cell(item.get('code', ''),        font_size=9, halign='CENTER'),
            make_cell(item.get('description', ''), font_size=9, wrap=True),
            make_cell(qty,                         font_size=9, halign='CENTER'),
            make_cell(item.get('rate', 0),         font_size=9,
                      halign='RIGHT', num_fmt=CURRENCY),
            make_cell(f'=IF(D{r}="","",D{r}*E{r})', font_size=9,
                      halign='RIGHT', num_fmt=CURRENCY),
            EC,
        ]})

    reqs.append({'updateCells': {
        'start': {'sheetId': SID, 'rowIndex': LI_START_ROW - 1, 'columnIndex': A},
        'rows':   li_rows,
        'fields': 'userEnteredValue,userEnteredFormat',
    }})

    # ── 5. Write totals ────────────────────────────────────────────────────────
    sum_range = f'F{LI_START_ROW}:F{last_item_row}'

    reqs.append({'updateCells': {
        'start': {'sheetId': SID, 'rowIndex': sub_row - 1, 'columnIndex': A},
        'rows': [
            {'values': [EC, EC, EC, EC,
                make_cell('Subtotal', font_size=10, halign='RIGHT'),
                make_cell(f'=IF(SUM({sum_range})=0,"",SUM({sum_range}))',
                          font_size=10, halign='RIGHT', num_fmt=CURRENCY),
                EC]},
            {'values': [EC, EC, EC, EC,
                make_cell('GST (10%)', font_size=10, halign='RIGHT'),
                make_cell(f'=IF(F{sub_row}="","",F{sub_row}*0.1)',
                          font_size=10, halign='RIGHT', num_fmt=CURRENCY),
                EC]},
            {'values': [EC, EC, EC, EC,
                make_cell('TOTAL', bold=True, font_size=11, halign='RIGHT'),
                make_cell(f'=IF(F{sub_row}="","",F{sub_row}+F{gst_row})',
                          bold=True, font_size=11, halign='RIGHT', num_fmt=CURRENCY),
                EC]},
        ],
        'fields': 'userEnteredValue,userEnteredFormat',
    }})

    # ── 6. Totals border ───────────────────────────────────────────────────────
    reqs.append({'updateBorders': {
        'range': gr(sub_row - 1, tot_row, E, F + 1),
        'top':             solid(EPS_BLUE),
        'bottom':          solid(EPS_BLUE, 2),
        'left':            solid(EPS_BLUE),
        'right':           solid(EPS_BLUE),
        'innerHorizontal': solid(LGRAY),
    }})

    # ── Execute ────────────────────────────────────────────────────────────────
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=ss_id,
        body={'requests': reqs}
    ).execute()

    print(f"Filled: {N} line item(s){f' (+{extra_rows} rows inserted)' if extra_rows else ''}")
    print(f"  Items:    rows {LI_START_ROW}–{last_item_row}")
    print(f"  Spacer:   row  {spacer_row}")
    print(f"  Subtotal: row  {sub_row}")
    print(f"  GST:      row  {gst_row}")
    print(f"  TOTAL:    row  {tot_row}")
    print(f"\nhttps://docs.google.com/spreadsheets/d/{ss_id}/edit")


if __name__ == '__main__':
    main()
