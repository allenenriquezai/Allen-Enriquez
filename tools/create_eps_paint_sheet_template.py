"""
Creates the EPS Paint quote Google Sheets template.
Run once. Saves sheet ID to pricing.json → sheet_templates.paint.

Usage:
    python3 tools/create_eps_paint_sheet_template.py

A4 sizing: each full-page image block = 44 rows × 21px = 924px
(A4 at 96dpi ≈ 1122px, minus 1-inch top+bottom margins ≈ 930px printable)

Column layout (6 columns, total 794px = A4 width):
  A (100px): Service Code / contact info
  B (344px): Description / main content
  C  (80px): QTY
  D (120px): Rate / totals label
  E (120px): Amount / deal ID / date
  F  (30px): Right margin

Layout (1-indexed rows):
  Rows   1–44  : COVER PAGE      — A:F merged (44 rows × 21px ≈ A4)
                  → INSERT cover page image over A1:F44 manually
                  → INSERT EPS Paint logo over A45:B49 manually (preserved on copy)
  Row   45     : phone bold (A:B merged) | [dealId] (E)
  Row   46     : email (A) | [quoteDate] (E)
  Row   47     : website (A)
  Row   48     : QBCC (A)
  Row   49     : spacer
  Row   50     : For: (A) | [organizationName] (B) | 8 Murarrie Road, (E)
  Row   51     : [personName] bold (B) | Murarrie QLD 4172 (E)
  Row   52     : [projectAddress] (B)
  Rows  53–54  : spacers (row 54 = 20px)
  Row   55     : JOB SPECIFICS bar (A:F merged, blue, 35px)
  Row   56     : spacer
  Rows  57–88  : [jobDescription] (A:E merged — wrapping description area)
  Rows  89–132 : SERVICES PAGE   — 44 rows × 21px ≈ A4, within description merge
                  → INSERT services page image over A89:F132 manually
  Row  133     : Table headers (A=Service Code, B=Description, C=QTY, D=Rate, E=Amount)
  Rows 134–158 : 25 line item rows (A=code | B=desc | C=qty | D=rate | E=C×D)
  Row  159     : Subtotal label (D) | =SUM(E134:E158) (E)
  Row  160     : GST (10%) label (D) | =E159*0.1 (E)
  Row  161     : TOTAL bold label (D) | =E159+E160 bold (E)
  Rows 162–205 : ACCEPTANCE PAGE — A:F merged (44 rows × 21px ≈ A4)
                  → INSERT acceptance page image over A162:F205 manually
  Rows 206–249 : CLOSING PAGE    — A:F merged (44 rows × 21px ≈ A4)
                  → INSERT closing page image over A206:F249 manually
"""

import json
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE  = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')
PRICING_CFG = os.path.join(BASE_DIR, 'projects', 'eps', 'config', 'pricing.json')

# ── Colours ────────────────────────────────────────────────────────────────────
def rgb(r, g, b): return {'red': r/255, 'green': g/255, 'blue': b/255}
EPS_BLUE = rgb(26,  60, 140)
WHITE    = rgb(255, 255, 255)
BLACK    = rgb(0,   0,   0)
LGRAY    = rgb(220, 220, 220)

# ── Column indices (0-indexed) ─────────────────────────────────────────────────
A, B, C, D, E, F = range(6)

# ── Sheet geometry ─────────────────────────────────────────────────────────────
SID        = 0
TOTAL_ROWS = 249
TOTAL_COLS = 6

# Each full-page image block: 44 rows × 21px = 924px ≈ A4 printable height
A4_ROWS = 44

# Cover page: rows 1–44 (0-idx 0–43)
COVER_END_IDX = A4_ROWS  # = 44 (exclusive end)

# Quote header: rows 45–56 (0-idx 44–55)
PHONE_IDX    = 44   # row 45
EMAIL_IDX    = 45   # row 46
WEB_IDX      = 46   # row 47
QBCC_IDX     = 47   # row 48
SPACER1_IDX  = 48   # row 49
FOR_IDX      = 49   # row 50
PERSON_IDX   = 50   # row 51
PROJADDR_IDX = 51   # row 52
SPACER2_IDX  = 52   # row 53
SPACER3_IDX  = 53   # row 54 (20px)
JOBSPEC_IDX  = 54   # row 55 (35px)
SPACER4_IDX  = 55   # row 56

DESC_IDX       = 56   # row 57 — start of description mega-merge
DESC_MERGE_END = 132  # exclusive (rows 57–131)

# Services page: rows 89–132 (0-idx 88–131), 44 rows × 21px ≈ A4
SERVICES_IDX = 88
SERVICES_END = 132  # exclusive

# Line items table: starts row 133 (0-idx 132)
LI_HEADER_IDX = 132  # row 133
LI_START_IDX  = 133  # row 134 (first line item)
LI_COUNT      = 25
LI_END_IDX    = LI_START_IDX + LI_COUNT  # = 158 (exclusive)
LI_START_ROW  = 134  # 1-indexed
LI_END_ROW    = 158  # 1-indexed (last item)

# Totals rows
SUBTOTAL_IDX = 158   # row 159
GST_IDX      = 159   # row 160
TOTAL_IDX    = 160   # row 161
F_SUBTOTAL   = 159   # 1-indexed formula ref
F_GST        = 160   # 1-indexed formula ref

# Acceptance page: rows 162–205 (0-idx 161–204), 44 rows × 21px ≈ A4
ACCEPT_IDX = 161
ACCEPT_END = 205   # exclusive

# Closing page: rows 206–249 (0-idx 205–248), 44 rows × 21px ≈ A4
CLOSE_IDX  = 205
CLOSE_END  = 249   # exclusive

CURRENCY = {'type': 'CURRENCY', 'pattern': '$#,##0.00'}


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_creds():
    if not os.path.exists(TOKEN_FILE):
        sys.exit("ERROR: Run python3 tools/auth_eps.py first")
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def gr(r1, r2, c1, c2):
    """GridRange (0-indexed, end-exclusive)."""
    return {'sheetId': SID,
            'startRowIndex': r1, 'endRowIndex': r2,
            'startColumnIndex': c1, 'endColumnIndex': c2}


def solid(color, width=1):
    return {'style': 'SOLID', 'width': width, 'color': color}


def cell(value=None, bold=False, font_size=10, fg=None, bg=None,
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
        'wrapStrategy': 'WRAP' if wrap else 'CLIP',
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


EC = cell()

def row(*cells):
    return {'values': list(cells)}


def put(sheet_api, ss_id, row_idx, col_idx, rows_data):
    return {
        'updateCells': {
            'start': {'sheetId': SID, 'rowIndex': row_idx, 'columnIndex': col_idx},
            'rows': rows_data,
            'fields': 'userEnteredValue,userEnteredFormat',
        }
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    creds  = get_creds()
    sheets = build('sheets', 'v4', credentials=creds)
    drive  = build('drive',  'v3', credentials=creds)

    with open(PRICING_CFG) as f:
        config = json.load(f)
    parent_id = config['eps_quotes_folder_id']

    # 1. Create spreadsheet
    ss = sheets.spreadsheets().create(body={
        'properties': {'title': 'EPS Paint — Quote Template'},
        'sheets': [{'properties': {
            'sheetId': SID, 'title': 'Quote', 'index': 0,
            'gridProperties': {'rowCount': TOTAL_ROWS, 'columnCount': TOTAL_COLS}
        }}]
    }).execute()
    ss_id  = ss['spreadsheetId']
    ss_url = f"https://docs.google.com/spreadsheets/d/{ss_id}/edit"

    # Move into EPS Quotes folder
    drive.files().update(
        fileId=ss_id,
        addParents=parent_id,
        removeParents='root',
        fields='id'
    ).execute()

    reqs = []

    # ── Column widths (total 794px = A4 width) ─────────────────────────────────
    for col, px in [(A, 100), (B, 344), (C, 80), (D, 120), (E, 120), (F, 30)]:
        reqs.append({'updateDimensionProperties': {
            'range': {'sheetId': SID, 'dimension': 'COLUMNS',
                      'startIndex': col, 'endIndex': col + 1},
            'properties': {'pixelSize': px}, 'fields': 'pixelSize'
        }})

    # ── Row heights ────────────────────────────────────────────────────────────
    # All rows default to 21px (A4-calibrated); only override exceptions:
    for r_idx, px in [
        (SPACER3_IDX,  20),   # row 54: tight spacer before JOB SPECIFICS
        (JOBSPEC_IDX,  35),   # row 55: JOB SPECIFICS bar
    ]:
        reqs.append({'updateDimensionProperties': {
            'range': {'sheetId': SID, 'dimension': 'ROWS',
                      'startIndex': r_idx, 'endIndex': r_idx + 1},
            'properties': {'pixelSize': px}, 'fields': 'pixelSize'
        }})
    # Line items + totals: 34px each (room for 2-line descriptions)
    reqs.append({'updateDimensionProperties': {
        'range': {'sheetId': SID, 'dimension': 'ROWS',
                  'startIndex': LI_START_IDX, 'endIndex': TOTAL_IDX + 1},
        'properties': {'pixelSize': 34}, 'fields': 'pixelSize'
    }})

    # ── Merges ─────────────────────────────────────────────────────────────────
    for merge in [
        # Cover page: rows 1–44 → A:F
        gr(0, COVER_END_IDX, A, TOTAL_COLS),

        # Phone row: A:B merged (wider phone text under logo)
        gr(PHONE_IDX, PHONE_IDX + 1, A, C),

        # JOB SPECIFICS bar: A:F
        gr(JOBSPEC_IDX, JOBSPEC_IDX + 1, A, TOTAL_COLS),

        # Description mega-merge: rows 57–131 → A:E
        # (services image floats over empty part of this cell)
        gr(DESC_IDX, DESC_MERGE_END, A, E + 1),

        # Acceptance page: rows 162–205 → A:F
        gr(ACCEPT_IDX, ACCEPT_END, A, TOTAL_COLS),

        # Closing page: rows 206–249 → A:F
        gr(CLOSE_IDX, CLOSE_END, A, TOTAL_COLS),
    ]:
        reqs.append({'mergeCells': {'range': merge, 'mergeType': 'MERGE_ALL'}})

    # ── Cell content ───────────────────────────────────────────────────────────

    # Row 45: phone bold (A:B merged) | [dealId] (E)
    reqs.append(put(sheets, ss_id, PHONE_IDX, A, [row(
        cell('0748 014 361', bold=True, font_size=10),   # A:B merged
        EC,
        EC,                                              # C
        EC,                                              # D
        cell('[dealID]', font_size=9, halign='RIGHT'),   # E
        EC,                                              # F
    )]))

    # Row 46: email (A) | [quoteDate] (E)
    reqs.append(put(sheets, ss_id, EMAIL_IDX, A, [row(
        cell('info@epspaint.com.au', font_size=9),
        EC, EC, EC,
        cell('[shortTodaysDate]', font_size=9, halign='RIGHT'),  # E
        EC,
    )]))

    # Row 47: website (A)
    reqs.append(put(sheets, ss_id, WEB_IDX, A, [row(
        cell('www.epspaint.com.au', font_size=9),
    )]))

    # Row 48: QBCC (A)
    reqs.append(put(sheets, ss_id, QBCC_IDX, A, [row(
        cell('QBCC: 15423647', font_size=9),
    )]))

    # Row 50: For: (A) | [organizationName] (B) | 8 Murarrie Road, (E)
    reqs.append(put(sheets, ss_id, FOR_IDX, A, [row(
        cell('For:', font_size=10),
        cell('[organizationName]', font_size=10),
        EC, EC,
        cell('8 Murarrie Road,', font_size=9, halign='RIGHT'),
        EC,
    )]))

    # Row 51: [personName] bold (B) | Murarrie QLD 4172 (E)
    reqs.append(put(sheets, ss_id, PERSON_IDX, A, [row(
        EC,
        cell('[personName]', bold=True, font_size=10),
        EC, EC,
        cell('Murarrie QLD 4172', font_size=9, halign='RIGHT'),
        EC,
    )]))

    # Row 52: [projectAddress] (B)
    reqs.append(put(sheets, ss_id, PROJADDR_IDX, B, [row(
        cell('[projectAddress]', font_size=10),
    )]))

    # Row 55: JOB SPECIFICS bar (A:F)
    reqs.append(put(sheets, ss_id, JOBSPEC_IDX, A, [row(
        cell('JOB SPECIFICS', bold=True, font_size=11,
             fg=WHITE, bg=EPS_BLUE, halign='CENTER'),
    )]))

    # Row 57: [jobDescription] (A:E merged, wrapping)
    reqs.append(put(sheets, ss_id, DESC_IDX, A, [row(
        cell('[jobDescription]', font_size=10, wrap=True),
    )]))

    # Row 133: table column headers (no merges — one column per header)
    reqs.append(put(sheets, ss_id, LI_HEADER_IDX, A, [row(
        cell('Service Code', bold=True, fg=WHITE, bg=EPS_BLUE, font_size=9, halign='CENTER'),  # A
        cell('Description',  bold=True, fg=WHITE, bg=EPS_BLUE, font_size=9, halign='CENTER'),  # B
        cell('QTY',          bold=True, fg=WHITE, bg=EPS_BLUE, font_size=9, halign='CENTER'),  # C
        cell('Rate',         bold=True, fg=WHITE, bg=EPS_BLUE, font_size=9, halign='CENTER'),  # D
        cell('Amount',       bold=True, fg=WHITE, bg=EPS_BLUE, font_size=9, halign='CENTER'),  # E
        EC,                                                                                      # F margin
    )]))

    # Rows 134–158: 25 line items
    li_rows = []
    for i in range(LI_COUNT):
        r = LI_START_ROW + i  # 1-indexed
        li_rows.append(row(
            cell(font_size=9, halign='CENTER'),                   # A: service code
            cell(font_size=9, wrap=True),                         # B: description
            cell(font_size=9, halign='CENTER'),                   # C: qty
            cell(font_size=9, halign='RIGHT', num_fmt=CURRENCY),  # D: rate
            cell(f'=IFERROR(C{r}*D{r},"")', font_size=9,         # E: amount = qty × rate
                 halign='RIGHT', num_fmt=CURRENCY),
            EC,                                                    # F: margin
        ))
    reqs.append(put(sheets, ss_id, LI_START_IDX, A, li_rows))

    # Rows 159–161: totals (label in D, value in E)
    reqs.append(put(sheets, ss_id, SUBTOTAL_IDX, A, [
        row(EC, EC, EC,
            cell('Subtotal', font_size=10, halign='RIGHT'),
            cell(f'=SUM(E{LI_START_ROW}:E{LI_END_ROW})',
                 font_size=10, halign='RIGHT', num_fmt=CURRENCY),
            EC),
        row(EC, EC, EC,
            cell('GST (10%)', font_size=10, halign='RIGHT'),
            cell(f'=E{F_SUBTOTAL}*0.1',
                 font_size=10, halign='RIGHT', num_fmt=CURRENCY),
            EC),
        row(EC, EC, EC,
            cell('TOTAL', bold=True, font_size=11, halign='RIGHT'),
            cell(f'=E{F_SUBTOTAL}+E{F_GST}',
                 bold=True, font_size=11, halign='RIGHT', num_fmt=CURRENCY),
            EC),
    ]))

    # ── Borders ────────────────────────────────────────────────────────────────

    # Outer border: header + line items (rows 133–158, cols A–E)
    reqs.append({'updateBorders': {
        'range': gr(LI_HEADER_IDX, LI_END_IDX, A, E + 1),
        'top':    solid(EPS_BLUE, 2),
        'bottom': solid(EPS_BLUE, 2),
        'left':   solid(EPS_BLUE, 2),
        'right':  solid(EPS_BLUE, 2),
    }})
    # Inner dividers for line items
    reqs.append({'updateBorders': {
        'range': gr(LI_START_IDX, LI_END_IDX, A, E + 1),
        'innerHorizontal': solid(LGRAY),
        'innerVertical':   solid(LGRAY),
    }})
    # Totals box (rows 159–161, cols D–E)
    reqs.append({'updateBorders': {
        'range': gr(SUBTOTAL_IDX, TOTAL_IDX + 1, D, E + 1),
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

    # ── Save ID to pricing.json ────────────────────────────────────────────────
    config.setdefault('sheet_templates', {})['paint'] = ss_id
    with open(PRICING_CFG, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Template created: {ss_url}")
    print(f"ID saved → pricing.json: sheet_templates.paint")
    print()
    print("Next steps — add images manually (Insert → Image → Image over cells):")
    print("  1. Cover page:     A1:F44   (44 rows × 21px = 924px ≈ A4)")
    print("  2. EPS Paint logo: A45:B49  (preserved on copy — do this once)")
    print("  3. Services page:  A89:F132 (44 rows × 21px = 924px ≈ A4)")
    print("  4. Acceptance:     A162:F205 (44 rows × 21px = 924px ≈ A4)")
    print("  5. Closing page:   A206:F249 (44 rows × 21px = 924px ≈ A4)")
    print()
    print("Tip: set print settings to A4 portrait, 'Fit to page width'.")
    print("Images are preserved when new quotes are copied from this template.")


if __name__ == '__main__':
    main()
