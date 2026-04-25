"""
e1_to_sheet.py — Push EstimateOne scrape data to Google Sheets.

Creates/updates an "EstimateOne — Tender Inbox" spreadsheet with tabs:
  - Open Tenders: available tenders within our area
  - Awarded: recently awarded projects (who won what)
  - Leads: tender invitations sent directly to EPS
  - Watchlist: tenders EPS is tracking
  - Log: scrape history and stats

Each run does a full refresh (clear + rewrite) per tab.

Usage:
    python tools/e1_to_sheet.py                            # use latest scrape
    python tools/e1_to_sheet.py --file path/to/scrape.json # use specific file
    python tools/e1_to_sheet.py --sheet-id XXXX            # write to existing sheet

Requires:
    projects/eps/token_eps.pickle (Google OAuth — run auth_eps.py first)
    projects/eps/.tmp/estimateone/e1_latest.json (from estimateone_scraper.py)
"""

import argparse
import json
import pickle
import sys
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
TOKEN_FILE = BASE_DIR / "projects" / "eps" / "token_eps.pickle"
DEFAULT_SCRAPE = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "e1_latest.json"
SHEET_ID_FILE = BASE_DIR / "projects" / "eps" / ".tmp" / "e1_sheet_id.txt"

TABS = ["Open Tenders", "Awarded", "Leads", "Watchlist", "Builder Directory", "Log"]


def get_creds():
    if not TOKEN_FILE.exists():
        print(f"ERROR: {TOKEN_FILE} not found. Run: python tools/auth_eps.py")
        sys.exit(1)
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return creds


def get_or_create_sheet(sheets_svc, sheet_id=None):
    if not sheet_id and SHEET_ID_FILE.exists():
        sheet_id = SHEET_ID_FILE.read_text().strip()

    if sheet_id:
        try:
            sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
            return sheet_id
        except Exception:
            print(f"Sheet {sheet_id} not accessible, creating new...")

    body = {
        "properties": {"title": "EstimateOne — Tender Inbox"},
        "sheets": [{"properties": {"title": t, "index": i}} for i, t in enumerate(TABS)],
    }
    result = sheets_svc.spreadsheets().create(body=body).execute()
    sheet_id = result["spreadsheetId"]

    SHEET_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    SHEET_ID_FILE.write_text(sheet_id)
    print(f"Created spreadsheet: https://docs.google.com/spreadsheets/d/{sheet_id}")
    return sheet_id


def ensure_tabs_exist(sheets_svc, sheet_id):
    """Make sure all required tabs exist."""
    spreadsheet = sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"] for s in spreadsheet["sheets"]}
    requests = []
    for tab in TABS:
        if tab not in existing:
            requests.append({"addSheet": {"properties": {"title": tab}}})
    if requests:
        sheets_svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()


def clear_and_write(sheets_svc, sheet_id, tab, rows):
    sheets_svc.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"'{tab}'!A:Z").execute()
    if rows:
        sheets_svc.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED", body={"values": rows},
        ).execute()
    print(f"  {tab}: {len(rows) - 1} rows")


def format_headers(sheets_svc, sheet_id):
    spreadsheet = sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    requests = []
    for sheet in spreadsheet["sheets"]:
        sid = sheet["properties"]["sheetId"]
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                }},
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        })
        requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        })
    if requests:
        sheets_svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()


# --- Formatters ---

def format_open_tenders(items):
    headers = ["Project", "Project ID", "Address", "Max Budget", "Distance",
               "Category", "Builder", "Quotes Due", "Added", "URL"]
    rows = [headers]
    for item in items:
        if "raw_page" in item:
            rows.append([item.get("note", "Raw dump"), "", "", "", "", "", "", "", "", ""])
            continue
        rows.append([
            item.get("project", item.get("title", "")),
            item.get("project_id", ""),
            item.get("address", ""),
            item.get("budget", ""),
            item.get("distance", ""),
            item.get("category", ""),
            item.get("builder", ""),
            item.get("quotes_due", ""),
            item.get("added", ""),
            item.get("url", ""),
        ])
    return rows


def format_awarded(items):
    headers = ["Project", "Project ID", "Address", "Max Budget", "Distance",
               "Category", "Builder", "Awarded Date", "URL"]
    rows = [headers]
    for item in items:
        if "raw_page" in item:
            rows.append([item.get("note", "Raw dump")] + [""] * 8)
            continue
        rows.append([
            item.get("project", item.get("title", "")),
            item.get("project_id", ""),
            item.get("address", ""),
            item.get("budget", ""),
            item.get("distance", ""),
            item.get("category", ""),
            item.get("builder", ""),
            item.get("quotes_due", item.get("added", "")),
            item.get("url", ""),
        ])
    return rows


def format_leads(items):
    headers = ["Project", "Project ID", "Builder", "Package", "Source",
               "Location", "Distance", "Budget", "Category", "Quotes Due",
               "Doc Status", "Quote Response", "Other Builders", "Flags"]
    rows = [headers]
    for item in items:
        if "raw_page" in item:
            rows.append([item.get("note", "")] + [""] * 13)
            continue
        rows.append([
            item.get("project", item.get("title", "")),
            item.get("project_id", ""),
            item.get("builder", ""),
            item.get("package", ""),
            item.get("source", ""),
            item.get("location", ""),
            item.get("distance", ""),
            item.get("budget", ""),
            item.get("category", ""),
            item.get("quotes_due", ""),
            item.get("doc_status", ""),
            item.get("quote_response", ""),
            ", ".join(item.get("other_builders", [])),
            ", ".join(item.get("flags", [])),
        ])
    return rows


def format_directory(items):
    headers = ["Builder", "Phone", "Fax", "Location", "Distance",
               "Current Tenders", "Awarded Tenders"]
    rows = [headers]
    # Sort by awarded desc
    sorted_items = sorted(items, key=lambda b: b.get("awarded_tenders", 0), reverse=True)
    for b in sorted_items:
        if "raw_page" in b:
            rows.append([b.get("note", "")] + [""] * 6)
            continue
        rows.append([
            b.get("name", ""),
            b.get("phone", ""),
            b.get("fax", ""),
            b.get("location", ""),
            b.get("distance", ""),
            b.get("current_tenders", 0),
            b.get("awarded_tenders", 0),
        ])
    return rows


def format_watchlist(items):
    headers = ["Title", "Details", "URL"]
    rows = [headers]
    for item in items:
        if "raw_page" in item:
            rows.append([item.get("note", ""), "", ""])
            continue
        rows.append([
            item.get("title", ""),
            item.get("full_text", " | ".join(item.get("raw_cells", [])))[:500],
            item.get("url", item.get("detail_url", "")),
        ])
    return rows


def append_log(sheets_svc, sheet_id, scrape_data):
    sections = scrape_data.get("sections", {})
    log_row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        scrape_data.get("scraped_at", ""),
        len(sections.get("open_tenders", [])),
        len(sections.get("awarded", [])),
        len(sections.get("leads", [])),
        len(sections.get("watchlist", [])),
        len(sections.get("directory", [])),
        "OK",
    ]
    # Ensure headers
    try:
        result = sheets_svc.spreadsheets().values().get(spreadsheetId=sheet_id, range="'Log'!A1:H1").execute()
        has_headers = bool(result.get("values"))
    except Exception:
        has_headers = False

    if not has_headers:
        sheets_svc.spreadsheets().values().update(
            spreadsheetId=sheet_id, range="'Log'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [["Pushed", "Scraped", "Open", "Awarded", "Leads", "Watchlist", "Builders", "Status"]]},
        ).execute()

    sheets_svc.spreadsheets().values().append(
        spreadsheetId=sheet_id, range="'Log'!A:H",
        valueInputOption="USER_ENTERED", body={"values": [log_row]},
    ).execute()


def main():
    parser = argparse.ArgumentParser(description="Push E1 scrape data to Google Sheets")
    parser.add_argument("--file", type=str, help="Path to scrape JSON")
    parser.add_argument("--sheet-id", type=str, help="Existing Google Sheet ID")
    args = parser.parse_args()

    scrape_file = Path(args.file) if args.file else DEFAULT_SCRAPE
    if not scrape_file.exists():
        print(f"ERROR: {scrape_file} not found. Run estimateone_scraper.py first.")
        sys.exit(1)

    scrape_data = json.loads(scrape_file.read_text())
    sections = scrape_data.get("sections", {})
    print(f"Loaded scrape from {scrape_file} (scraped: {scrape_data.get('scraped_at', '?')})")

    creds = get_creds()
    sheets_svc = build("sheets", "v4", credentials=creds)

    sheet_id = get_or_create_sheet(sheets_svc, args.sheet_id)
    ensure_tabs_exist(sheets_svc, sheet_id)
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}")

    # Write each section
    if "open_tenders" in sections:
        clear_and_write(sheets_svc, sheet_id, "Open Tenders", format_open_tenders(sections["open_tenders"]))
    if "awarded" in sections:
        clear_and_write(sheets_svc, sheet_id, "Awarded", format_awarded(sections["awarded"]))
    if "leads" in sections:
        clear_and_write(sheets_svc, sheet_id, "Leads", format_leads(sections["leads"]))
    if "watchlist" in sections:
        clear_and_write(sheets_svc, sheet_id, "Watchlist", format_watchlist(sections["watchlist"]))
    if "directory" in sections:
        clear_and_write(sheets_svc, sheet_id, "Builder Directory", format_directory(sections["directory"]))

    append_log(sheets_svc, sheet_id, scrape_data)
    format_headers(sheets_svc, sheet_id)

    print(f"\nDone. https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == "__main__":
    main()
