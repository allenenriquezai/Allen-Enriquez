"""
Personal Brand CRM Manager.

Manages Allen's Google Sheets CRM for cold-calling painting companies in Charlotte NC.

Subcommands:
    clean          One-time sheet cleanup (reorder cols, format, dedupe, normalise)
    evening-brief  Send evening briefing email (priority call list + personal calendar/inbox)
    cleanup        Post-calling CRM normalisation (automated at 12:30 AM via launchd)
    draft          Draft outreach email for a specific lead
    review         Print terminal summary of CRM priorities

Usage:
    python3 tools/personal_crm.py clean --dry-run
    python3 tools/personal_crm.py clean
    python3 tools/personal_crm.py evening-brief --dry-run
    python3 tools/personal_crm.py evening-brief
    python3 tools/personal_crm.py cleanup --dry-run
    python3 tools/personal_crm.py cleanup
    python3 tools/personal_crm.py draft --row 3 --tab "Painting Companies"
    python3 tools/personal_crm.py review

Requires:
    projects/personal/token_personal.pickle: Google OAuth token with Sheets + Gmail + Calendar
"""

import argparse
import base64
import json
import os
import pickle
import re
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'personal_crm.json'
CLEANUP_LOG = TMP_DIR / 'personal_crm_cleanup.log'
TEMPLATE_DIR = BASE_DIR / 'projects' / 'personal' / 'templates' / 'email'

SPREADSHEET_ID = '1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8'
TABS = ['Painting Companies', 'Others']

BRIEFING_FROM = 'allenenriquez@gmail.com'
BRIEFING_TO = 'allenenriquez006@gmail.com'

# --- Column order ---
# A-I = Allen's primary view (zoomed in)
PRIMARY_COLS = [
    'Business Name', 'Decision Maker', 'Phone', 'Call Outcome', 'Notes',
    'Follow-up Date', 'Date Called', 'Email', 'Website',
]
SECONDARY_COLS = [
    'Date Emailed', 'City', 'Service Areas', 'Social Media', 'LinkedIn',
    'BBB Rating', 'Connected', 'Source', 'BBB URL',
]
TARGET_HEADERS = PRIMARY_COLS + SECONDARY_COLS

# --- Call outcome classifications ---
HOT_OUTCOMES = {'Warm Interest', 'Meeting Booked'}
ACTION_OUTCOMES = {'Asked For Email', 'Call Back', 'Late Follow Up'}
CALLBACK_OUTCOMES = {'No Answer 1', 'No Answer 2', 'No Answer 3', 'No Answer 4', 'No Answer 5'}
DEAD_OUTCOMES = {'Not Interested - Convo', 'Not Interested - No Convo', 'Invalid Number'}

DROPDOWN_VALUES = [
    'New / No Label', 'No Answer 1', 'No Answer 2', 'No Answer 3',
    'No Answer 4', 'No Answer 5', 'Not Interested - No Convo',
    'Not Interested - Convo', 'Invalid Number', 'Call Back',
    'Asked For Email', 'Late Follow Up', 'Warm Interest', 'Meeting Booked',
]

# Conditional format colours (RGB 0-1)
COLOUR_GREEN = {'red': 0.863, 'green': 0.988, 'blue': 0.906}   # #dcfce7
COLOUR_YELLOW = {'red': 0.996, 'green': 0.976, 'blue': 0.765}  # #fef9c3
COLOUR_GREY = {'red': 0.937, 'green': 0.941, 'blue': 0.945}    # #eff0f1
COLOUR_RED = {'red': 0.996, 'green': 0.886, 'blue': 0.886}     # #fee2e2
COLOUR_HEADER_BG = {'red': 0.118, 'green': 0.161, 'blue': 0.231}  # #1e293b
COLOUR_ALT_ROW = {'red': 0.973, 'green': 0.98, 'blue': 0.984}  # #f8f9fa
COLOUR_WHITE = {'red': 1, 'green': 1, 'blue': 1}

# Day name lookup for relative date parsing
DAY_NAMES = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
}


# ============================================================
# Google API helpers
# ============================================================

def load_token():
    if not TOKEN_FILE.exists():
        print(f"ERROR: token not found at {TOKEN_FILE}")
        print("Run: python3 tools/auth_personal.py")
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def get_sheets_service():
    return build('sheets', 'v4', credentials=load_token())


def get_gmail_service():
    return build('gmail', 'v1', credentials=load_token())


def get_calendar_service():
    return build('calendar', 'v3', credentials=load_token())


# ============================================================
# Note parsing (regex only, no LLM)
# ============================================================

def parse_notes(text):
    """Parse free-form notes. Returns dict with entries, todos, follow_up_date, personal_details."""
    if not text.strip():
        return {'entries': [], 'todos': [], 'follow_up_date': '', 'follow_up_source': '', 'personal_details': []}

    # Split on ____ or date-like headers
    entries = re.split(r'_{3,}', text)

    todos = []
    follow_up_date = ''
    follow_up_source = ''
    personal_details = []

    for entry in entries:
        # Extract TODOs
        todo_matches = re.findall(r'TO\s*DO\s*:?\s*(.+?)(?:\n|$)', entry, re.IGNORECASE)
        todos.extend([t.strip() for t in todo_matches])

        # Extract "call back" / "follow up" phrases with dates
        callback_patterns = [
            r'(?:call\s*back|follow\s*up)(?:\s+(?:on|in|around|by))?\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)(?!\d)',
            r'(?:call\s*back|follow\s*up).*?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?:call\s*back|follow\s*up).*?(?:next\s+week\s+)(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?:call\s*back|follow\s*up).*?(mid\s+next\s+week)',
        ]
        for pat in callback_patterns:
            m = re.search(pat, entry, re.IGNORECASE)
            if m and not follow_up_date:
                raw = m.group(1).strip().lower()
                resolved = resolve_relative_date(raw)
                if resolved:
                    follow_up_date = resolved
                    follow_up_source = 'notes_parsed'
                else:
                    follow_up_date = m.group(1).strip()
                    follow_up_source = 'notes_raw'

        # Extract personal details ("likes X", "NAME likes X")
        likes = re.findall(r'(?:\w+\s+)?likes?\s+(\w[\w\s]*?)(?:\s*[-–—.]|\s*$)', entry, re.IGNORECASE)
        for like in likes:
            detail = like.strip()
            if detail.lower() not in ('to', 'the', 'a', 'an', 'that', 'it', 'this'):
                # Reconstruct with context
                ctx = re.search(r'(\w+)\s+likes?\s+' + re.escape(detail), entry, re.IGNORECASE)
                if ctx:
                    personal_details.append(f"{ctx.group(1)} likes {detail}")
                else:
                    personal_details.append(f"likes {detail}")

    return {
        'entries': [e.strip() for e in entries if e.strip()],
        'todos': todos,
        'follow_up_date': follow_up_date,
        'follow_up_source': follow_up_source,
        'personal_details': list(set(personal_details)),
    }


def resolve_relative_date(raw):
    """Try to resolve a relative date string to YYYY-MM-DD. Returns '' if can't."""
    today = datetime.now().date()

    # "mid next week" → next Wednesday
    if 'mid next week' in raw:
        days_ahead = (2 - today.weekday()) % 7 + 7  # next Wednesday
        return (today + timedelta(days=days_ahead)).isoformat()

    # Day name: "tuesday", "next week tuesday"
    for name, dow in DAY_NAMES.items():
        if name in raw:
            days_ahead = (dow - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            if 'next week' in raw:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).isoformat()

    # Date pattern: 4/15, 04-15-2026 (reject phone-number fragments)
    m = re.match(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$', raw)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        if month > 12 or day > 31:
            return ''
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            pass

    return ''


# ============================================================
# Row parsing and classification
# ============================================================

def get_cell(row, col_map, name):
    """Safely get a cell value by column name."""
    i = col_map.get(name)
    if i is None or i >= len(row):
        return ''
    return str(row[i]).strip()


def parse_row(row, col_map, tab, row_num):
    """Parse a sheet row into a normalised lead dict."""
    # Handle header aliases
    dm_key = 'Decision Maker' if 'Decision Maker' in col_map else 'Owner Name / DM'

    name = get_cell(row, col_map, 'Business Name')
    if not name:
        return None

    notes_text = get_cell(row, col_map, 'Notes')
    parsed = parse_notes(notes_text)

    follow_up_col = get_cell(row, col_map, 'Follow-up Date')
    follow_up_date = follow_up_col or parsed['follow_up_date']
    follow_up_source = 'column' if follow_up_col else parsed['follow_up_source']

    return {
        'tab': tab,
        'row_num': row_num,
        'business_name': name,
        'decision_maker': get_cell(row, col_map, dm_key),
        'phone': get_cell(row, col_map, 'Phone'),
        'call_outcome': get_cell(row, col_map, 'Call Outcome'),
        'notes': notes_text,
        'notes_truncated': notes_text[:200] if notes_text else '',
        'date_called': get_cell(row, col_map, 'Date Called'),
        'date_emailed': get_cell(row, col_map, 'Date Emailed'),
        'email': get_cell(row, col_map, 'Email'),
        'website': get_cell(row, col_map, 'Website'),
        'follow_up_date': follow_up_date,
        'follow_up_source': follow_up_source,
        'todos': parsed['todos'],
        'personal_details': parsed['personal_details'],
        'source': get_cell(row, col_map, 'Source'),
    }


def classify_lead(lead):
    """Classify a lead into priority bucket."""
    outcome = lead['call_outcome']
    today = datetime.now().date().isoformat()

    if not outcome or outcome == 'New / No Label':
        return 'uncalled', 'LOW'

    if outcome in HOT_OUTCOMES:
        if lead['follow_up_date'] and lead['follow_up_date'] <= today:
            return 'hot_lead', 'URGENT'
        return 'hot_lead', 'HIGH'

    if outcome == 'Asked For Email':
        if not lead['date_emailed']:
            return 'email_needed', 'HIGH'
        return 'follow_up', 'MEDIUM'

    if outcome == 'Call Back':
        if lead['follow_up_date'] and lead['follow_up_date'] <= today:
            return 'callback', 'HIGH'
        return 'callback', 'MEDIUM'

    if outcome == 'Late Follow Up':
        return 'follow_up', 'MEDIUM'

    if outcome in CALLBACK_OUTCOMES:
        return 'no_answer', 'MEDIUM'

    if outcome in DEAD_OUTCOMES:
        return 'dead', 'LOW'

    return 'other', 'LOW'


# ============================================================
# CRM scan — reads sheet, builds JSON
# ============================================================

def scan_crm():
    """Read both tabs, parse all rows, return structured data."""
    service = get_sheets_service()
    all_leads = []

    for tab in TABS:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        rows = result.get('values', [])
        if not rows:
            continue

        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}

        for i, row in enumerate(rows[1:], start=2):
            lead = parse_row(row, col_map, tab, i)
            if lead:
                lead_type, priority = classify_lead(lead)
                lead['type'] = lead_type
                lead['priority'] = priority
                lead['needs_email'] = (
                    lead['call_outcome'] in (HOT_OUTCOMES | {'Asked For Email'})
                    and not lead['date_emailed']
                )
                all_leads.append(lead)

    # Sort by priority
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    all_leads.sort(key=lambda x: priority_order.get(x['priority'], 4))

    # Build output
    action_items = [l for l in all_leads if l['type'] not in ('uncalled', 'dead')]
    hot_leads = [l for l in all_leads if l['type'] == 'hot_lead']
    today = datetime.now().date().isoformat()
    due_today = [l for l in action_items if l.get('follow_up_date') == today]
    overdue = [l for l in action_items if l.get('follow_up_date') and l['follow_up_date'] < today]

    stats = {
        'total': len(all_leads),
        'hot': len(hot_leads),
        'callbacks': len([l for l in all_leads if l['type'] in ('callback', 'no_answer')]),
        'emails_pending': len([l for l in all_leads if l['needs_email']]),
        'uncalled': len([l for l in all_leads if l['type'] == 'uncalled']),
        'dead': len([l for l in all_leads if l['type'] == 'dead']),
    }

    output = {
        'generated_at': datetime.now().isoformat(),
        'date': today,
        'stats': stats,
        'action_items': action_items,
        'hot_leads': hot_leads,
        'due_today': due_today,
        'overdue': overdue,
        'sheet_url': f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}',
    }

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, default=str))
    return output


# ============================================================
# clean — one-time sheet cleanup
# ============================================================

def cmd_clean(args):
    service = get_sheets_service()
    sheet_meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets_info = {s['properties']['title']: s['properties']['sheetId'] for s in sheet_meta['sheets']}

    changes_log = []

    for tab in TABS:
        sheet_id = sheets_info[tab]
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        rows = result.get('values', [])
        if not rows:
            continue

        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}
        data = rows[1:]

        # --- Normalise outcomes (both tabs) ---
        updates = []
        outcome_idx = col_map.get('Call Outcome')
        notes_idx = col_map.get('Notes')
        followup_idx = col_map.get('Follow-up Date')

        for i, row in enumerate(data, start=2):
            outcome = get_cell(row, col_map, 'Call Outcome')
            notes = get_cell(row, col_map, 'Notes')

            if not outcome and notes:
                # Check if notes mention TODO/callback
                parsed = parse_notes(notes)
                if parsed['todos'] or re.search(r'call\s*back', notes, re.IGNORECASE):
                    new_outcome = 'Call Back'
                    if parsed['follow_up_date'] and followup_idx is not None:
                        updates.append({
                            'row': i, 'col_letter': chr(65 + followup_idx),
                            'value': parsed['follow_up_date'],
                            'desc': f"Row {i}: Follow-up Date = {parsed['follow_up_date']}"
                        })
                else:
                    new_outcome = 'New / No Label'

                updates.append({
                    'row': i, 'col_letter': chr(65 + outcome_idx),
                    'value': new_outcome,
                    'desc': f"Row {i} ({get_cell(row, col_map, 'Business Name')}): Call Outcome '' → '{new_outcome}'"
                })

        if args.dry_run:
            print(f"\n[{tab}] Would make {len(updates)} updates:")
            for u in updates[:20]:
                print(f"  {u['desc']}")
            if len(updates) > 20:
                print(f"  ... and {len(updates) - 20} more")
        else:
            changes_log.append(f"[{tab}] Made {len(updates)} outcome/follow-up updates")

    # --- Structural + formatting changes (both tabs) ---
    if args.dry_run:
        print("\n[Structure] Would reorder columns to:", PRIMARY_COLS[:9])
        print("[Structure] Would sort called leads to top (hot → action → callbacks → rest)")
        print("[Structure] Would align Others headers to match Painting Companies")
        print("[Formatting] Would apply: header styling, alternating rows, conditional formatting on Call Outcome, dropdown validation")
        print(f"\nTotal changes: preview complete. Run without --dry-run to apply.")
        return

    # Apply data changes + reorder for each tab
    for tab in TABS:
        tab_result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        tab_rows = tab_result.get('values', [])
        if not tab_rows:
            continue

        tab_headers = tab_rows[0]
        tab_col_map = {h: i for i, h in enumerate(tab_headers)}
        tab_data = tab_rows[1:]

        # Apply outcome/follow-up updates
        outcome_idx = tab_col_map.get('Call Outcome')
        notes_idx = tab_col_map.get('Notes')
        followup_idx = tab_col_map.get('Follow-up Date')
        batch_updates = []

        if outcome_idx is not None:
            for i, row in enumerate(tab_data, start=2):
                outcome = get_cell(row, tab_col_map, 'Call Outcome')
                notes = get_cell(row, tab_col_map, 'Notes')

                if not outcome and notes:
                    parsed = parse_notes(notes)
                    if parsed['todos'] or re.search(r'call\s*back', notes, re.IGNORECASE):
                        new_outcome = 'Call Back'
                        if parsed['follow_up_date'] and followup_idx is not None:
                            batch_updates.append({
                                'range': f"'{tab}'!{chr(65 + followup_idx)}{i}",
                                'values': [[parsed['follow_up_date']]]
                            })
                    else:
                        new_outcome = 'New / No Label'

                    batch_updates.append({
                        'range': f"'{tab}'!{chr(65 + outcome_idx)}{i}",
                        'values': [[new_outcome]]
                    })

        if batch_updates:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'RAW', 'data': batch_updates}
            ).execute()
            changes_log.append(f"[{tab}] Applied {len(batch_updates)} outcome/follow-up updates")

        # Re-read after updates, then reorder columns + sort (called leads on top)
        tab_result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        tab_rows = tab_result.get('values', [])
        tab_headers = tab_rows[0]
        tab_col_map = {h: i for i, h in enumerate(tab_headers)}

        # Handle header aliases
        alias_map = {'Decision Maker': 'Owner Name / DM'}

        new_tab = [TARGET_HEADERS]
        called_rows = []
        uncalled_rows = []

        for row in tab_rows[1:]:
            new_row = []
            for h in TARGET_HEADERS:
                # Try direct match first, then alias
                idx = tab_col_map.get(h)
                if idx is None and h in alias_map:
                    idx = tab_col_map.get(alias_map[h])
                if idx is not None and idx < len(row):
                    new_row.append(row[idx])
                else:
                    new_row.append('')

            # Sort: called leads (have outcome or notes) go to top
            outcome = new_row[3]  # Call Outcome is index 3
            notes = new_row[4]    # Notes is index 4
            if outcome or notes:
                called_rows.append(new_row)
            else:
                uncalled_rows.append(new_row)

        # Within called rows, sort by priority: hot first, then action, then callbacks, then rest
        def sort_key(row):
            outcome = row[3]
            if outcome in HOT_OUTCOMES:
                return 0
            if outcome in ACTION_OUTCOMES:
                return 1
            if outcome in CALLBACK_OUTCOMES:
                return 2
            if outcome in DEAD_OUTCOMES:
                return 4
            return 3

        called_rows.sort(key=sort_key)
        new_tab.extend(called_rows)
        new_tab.extend(uncalled_rows)

        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
            valueInputOption='RAW', body={'values': new_tab}
        ).execute()
        changes_log.append(f"[{tab}] Reordered columns, sorted {len(called_rows)} called leads to top")

    # --- Apply formatting to both tabs ---
    for tab in TABS:
        sid = sheets_info[tab]
        apply_formatting(service, sid, tab)

    for line in changes_log:
        print(line)
    print("Sheet cleanup complete.")


def apply_formatting(service, sheet_id, tab):
    """Apply visual formatting: header, alternating rows, conditional formatting, dropdown."""
    requests = []

    # Freeze header row
    requests.append({
        'updateSheetProperties': {
            'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
            'fields': 'gridProperties.frozenRowCount'
        }
    })

    # Header row styling: dark bg, white bold text
    requests.append({
        'repeatCell': {
            'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': COLOUR_HEADER_BG,
                    'textFormat': {'bold': True, 'foregroundColor': COLOUR_WHITE, 'fontSize': 10},
                    'horizontalAlignment': 'CENTER',
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    })

    # Alternating row colours (rows 2+)
    requests.append({
        'addBanding': {
            'bandedRange': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': len(TARGET_HEADERS)},
                'rowProperties': {
                    'firstBandColor': COLOUR_WHITE,
                    'secondBandColor': COLOUR_ALT_ROW,
                },
            }
        }
    })

    # Conditional formatting on Call Outcome (column D = index 3)
    outcome_col = 3  # Call Outcome is always column D after reorder
    cf_rules = [
        ({'Warm Interest', 'Meeting Booked'}, COLOUR_GREEN),
        ({'Asked For Email', 'Call Back', 'Late Follow Up'}, COLOUR_YELLOW),
        ({'No Answer 1', 'No Answer 2', 'No Answer 3', 'No Answer 4', 'No Answer 5'}, COLOUR_GREY),
        ({'Not Interested - Convo', 'Not Interested - No Convo', 'Invalid Number'}, COLOUR_RED),
    ]

    for values, colour in cf_rules:
        for val in values:
            requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': len(TARGET_HEADERS)}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': f'=$D2="{val}"'}]
                            },
                            'format': {'backgroundColor': colour}
                        }
                    },
                    'index': 0
                }
            })

    # Data validation dropdown on Call Outcome column (all data rows)
    requests.append({
        'setDataValidation': {
            'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': outcome_col, 'endColumnIndex': outcome_col + 1},
            'rule': {
                'condition': {
                    'type': 'ONE_OF_LIST',
                    'values': [{'userEnteredValue': v} for v in DROPDOWN_VALUES]
                },
                'strict': True,
                'showCustomUi': True,
            }
        }
    })

    # Auto-resize columns A-I
    requests.append({
        'autoResizeDimensions': {
            'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 9}
        }
    })

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={'requests': requests}
    ).execute()
    print(f"  [{tab}] Formatting applied")


# ============================================================
# cleanup — automated post-calling normalisation
# ============================================================

def cmd_cleanup(args):
    service = get_sheets_service()
    changes = []

    for tab in TABS:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) < 2:
            continue

        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}
        outcome_idx = col_map.get('Call Outcome')
        followup_idx = col_map.get('Follow-up Date')
        notes_idx = col_map.get('Notes')

        if outcome_idx is None:
            continue

        batch_updates = []
        for i, row in enumerate(rows[1:], start=2):
            outcome = get_cell(row, col_map, 'Call Outcome')
            notes = get_cell(row, col_map, 'Notes')
            name = get_cell(row, col_map, 'Business Name')
            followup = get_cell(row, col_map, 'Follow-up Date') if followup_idx else ''

            # Normalise empty outcomes with notes
            if not outcome and notes:
                parsed = parse_notes(notes)
                if parsed['todos'] or re.search(r'call\s*back', notes, re.IGNORECASE):
                    new_outcome = 'Call Back'
                else:
                    new_outcome = 'New / No Label'
                batch_updates.append({
                    'range': f"'{tab}'!{chr(65 + outcome_idx)}{i}",
                    'values': [[new_outcome]]
                })
                changes.append(f"  [{tab}] Row {i} ({name}): outcome → '{new_outcome}'")

            # Fill empty follow-up date from notes
            if not followup and notes and followup_idx is not None:
                parsed = parse_notes(notes)
                if parsed['follow_up_date'] and parsed['follow_up_source'] == 'notes_parsed':
                    batch_updates.append({
                        'range': f"'{tab}'!{chr(65 + followup_idx)}{i}",
                        'values': [[parsed['follow_up_date']]]
                    })
                    changes.append(f"  [{tab}] Row {i} ({name}): follow-up → {parsed['follow_up_date']}")

        if args.dry_run:
            # Print only this tab's changes (skip previously printed ones)
            tab_changes = [c for c in changes if f'[{tab}]' in c]
            for c in tab_changes:
                print(c)
        elif batch_updates:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'RAW', 'data': batch_updates}
            ).execute()

    # Always run a scan to update the cache
    data = scan_crm()

    # Log
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    log_entry = f"[{timestamp}] Cleanup: {len(changes)} changes\n"
    for c in changes:
        log_entry += c + '\n'
    with open(CLEANUP_LOG, 'a') as f:
        f.write(log_entry + '\n')

    if args.dry_run:
        print(f"\nWould make {len(changes)} changes. Run without --dry-run to apply.")
    else:
        print(f"Cleanup done: {len(changes)} changes. Cache updated at {OUTPUT_FILE}")


# ============================================================
# review — terminal summary
# ============================================================

def cmd_review(args):
    if not OUTPUT_FILE.exists():
        print("No cached data. Running scan...")
        data = scan_crm()
    else:
        data = json.loads(OUTPUT_FILE.read_text())

    stats = data['stats']
    print(f"\n{'='*50}")
    print(f"Personal Brand CRM — {data['date']}")
    print(f"{'='*50}")
    print(f"Total: {stats['total']} | Hot: {stats['hot']} | Callbacks: {stats['callbacks']} | "
          f"Emails pending: {stats['emails_pending']} | Uncalled: {stats['uncalled']} | Dead: {stats['dead']}")
    print()

    if data['overdue']:
        print("OVERDUE:")
        for item in data['overdue'][:10]:
            print(f"  {item['priority']} | {item['business_name']} ({item['decision_maker']}) | "
                  f"{item['call_outcome']} | Due: {item['follow_up_date']} | {item['phone']}")
        print()

    if data['due_today']:
        print("DUE TODAY:")
        for item in data['due_today']:
            print(f"  {item['priority']} | {item['business_name']} ({item['decision_maker']}) | "
                  f"{item['call_outcome']} | {item['phone']}")
        print()

    if data['hot_leads']:
        print("HOT LEADS:")
        for item in data['hot_leads']:
            details = ', '.join(item.get('personal_details', []))
            print(f"  {item['priority']} | {item['business_name']} ({item['decision_maker']}) | "
                  f"{item['call_outcome']} | {item['phone']}")
            if details:
                print(f"    Personal: {details}")
            if item.get('todos'):
                print(f"    TODO: {'; '.join(item['todos'])}")
        print()

    print(f"Sheet: {data['sheet_url']}")


# ============================================================
# evening-brief — send evening briefing email
# ============================================================

# Email filtering (copied from morning_briefing.py)
PROMO_SENDERS = [
    'noreply@', 'no-reply@', 'newsletter@', 'marketing@', 'promo@',
    'updates@', 'notifications@', 'info@', 'hello@', 'news@',
    'mailchimp.com', 'sendgrid.net', 'hubspot', 'mailgun',
    'constantcontact', 'campaignmonitor', 'sendinblue', 'klaviyo',
    'intercom', 'drip.com', 'convertkit', 'substack',
    'linkedin.com', 'facebookmail', 'accounts.google',
    'notion.so', 'slack.com', 'atlassian', 'trello',
    'canva.com', 'dropbox.com', 'zoom.us',
    'justcall', 'justcall.io',
]

PROMO_SUBJECTS = [
    'unsubscribe', 'weekly digest', 'newsletter', 'your daily',
    'new features', 'product update', 'special offer', 'limited time',
    'flash sale', 'don\'t miss', 'act now', 'exclusive deal',
]


def is_promotional(email):
    sender = email.get('from', '').lower()
    subject = email.get('subject', '').lower()
    if any(p in sender for p in PROMO_SENDERS):
        return True
    if any(p in subject for p in PROMO_SUBJECTS):
        return True
    return False


def fetch_personal_gmail(max_results=20):
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()
            headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
            emails.append({
                'subject': headers.get('Subject', '(no subject)'),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': detail.get('snippet', ''),
            })
        emails = [e for e in emails if not is_promotional(e)]
        return emails
    except Exception as e:
        print(f"  [Gmail] Failed: {e}")
        return []


def fetch_personal_calendar():
    try:
        service = get_calendar_service()
        now = datetime.now(timezone.utc)
        # Get events from now until end of day
        end = now.replace(hour=23, minute=59, second=59)
        results = service.events().list(
            calendarId='primary', timeMin=now.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy='startTime', maxResults=20
        ).execute()
        events = []
        for evt in results.get('items', []):
            start = evt['start'].get('dateTime', evt['start'].get('date', ''))
            events.append({
                'title': evt.get('summary', '(no title)'),
                'start': start,
                'location': evt.get('location', ''),
            })
        return events
    except Exception as e:
        print(f"  [Calendar] Failed: {e}")
        return []


def format_time(time_str):
    if 'T' in time_str:
        try:
            return datetime.fromisoformat(time_str).strftime('%I:%M %p')
        except ValueError:
            pass
    return time_str


def build_evening_html(crm_data, calendar, emails):
    """Build evening briefing HTML email."""
    today = datetime.now().strftime('%A, %d %B %Y')
    stats = crm_data['stats']
    action_items = crm_data.get('action_items', [])
    hot_leads = crm_data.get('hot_leads', [])
    due_today = crm_data.get('due_today', [])
    overdue = crm_data.get('overdue', [])

    CARD = 'background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px;'
    AMBER = CARD + ' border-left: 4px solid #f59e0b;'
    BLUE = CARD + ' border-left: 4px solid #3b82f6;'
    GREEN = CARD + ' border-left: 4px solid #22c55e;'
    HEADER = 'background: #1e293b; color: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 16px; font-weight: 600;'
    PILL = 'display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px;'

    priority_icons = {'URGENT': '&#128308;', 'HIGH': '&#128992;', 'MEDIUM': '&#128993;', 'LOW': '&#9898;'}

    action_count = len(hot_leads) + len(due_today) + len(overdue)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f1f5f9; padding: 20px; margin: 0;">

<div style="max-width: 640px; margin: 0 auto;">
  <h1 style="text-align: center; color: #1e293b; font-size: 22px; margin-bottom: 4px;">Evening Briefing</h1>
  <p style="text-align: center; color: #64748b; font-size: 14px; margin-top: 0;">{today}</p>

  <div style="text-align: center; margin-bottom: 20px;">
    <span style="{PILL} background: #dcfce7; color: #166534;">{stats['hot']} hot</span>
    <span style="{PILL} background: #fef9c3; color: #854d0e;">{stats['callbacks']} callbacks</span>
    <span style="{PILL} background: #dbeafe; color: #1e40af;">{stats['emails_pending']} emails pending</span>
    <span style="{PILL} background: #f1f5f9; color: #475569;">{stats['uncalled']} uncalled</span>
  </div>
"""

    # Priority call list
    priority_items = overdue + due_today + [l for l in hot_leads if l not in due_today and l not in overdue]
    # Add callbacks and follow-ups
    callbacks = [l for l in action_items if l['type'] in ('callback', 'no_answer', 'email_needed', 'follow_up') and l not in priority_items]
    priority_items.extend(callbacks[:10])

    if priority_items:
        html += f'  <div style="{HEADER}">Priority Call List ({len(priority_items)})</div>\n'

        for item in priority_items:
            icon = priority_icons.get(item['priority'], '&#9898;')
            badge = ''
            if item in overdue:
                badge = '<span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">OVERDUE</span>'
            elif item in due_today:
                badge = '<span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">DUE TODAY</span>'

            card_style = AMBER if item['priority'] in ('URGENT', 'HIGH') else CARD

            details_html = ''
            if item.get('personal_details'):
                details_html = f'<div style="font-size: 12px; color: #7c3aed; margin-top: 4px;">&#128172; {", ".join(item["personal_details"])}</div>'

            todos_html = ''
            if item.get('todos'):
                todos_html = f'<div style="font-size: 12px; color: #dc2626; margin-top: 4px;">&#9888; {"; ".join(item["todos"])}</div>'

            notes_html = ''
            if item.get('notes_truncated'):
                snippet = item['notes_truncated'][:150].replace('\n', ' ')
                notes_html = f'<div style="font-size: 12px; color: #64748b; margin-top: 4px; font-style: italic;">{snippet}...</div>'

            html += f"""  <div style="{card_style}">
    <div style="font-size: 14px; font-weight: 600; color: #1e293b;">
      {icon} {item['business_name']}{badge}
    </div>
    <div style="font-size: 13px; color: #475569; margin-top: 4px;">
      {item['decision_maker']} &middot; {item['call_outcome']}
      {f" &middot; Follow-up: {item['follow_up_date']}" if item.get('follow_up_date') else ''}
    </div>
    <div style="font-size: 13px; margin-top: 6px;">
      &#128222; <a href="tel:{item['phone']}" style="color: #2563eb; text-decoration: none;">{item['phone']}</a>
      {f' &middot; &#9993; <a href="mailto:{item["email"]}" style="color: #2563eb; text-decoration: none;">{item["email"]}</a>' if item.get('email') else ''}
    </div>
    {details_html}{todos_html}{notes_html}
  </div>
"""

    # Calendar
    if calendar:
        html += f'  <div style="{HEADER}">Tonight\'s Schedule</div>\n'
        html += f'  <div style="{CARD}">\n'
        for evt in calendar:
            time_str = format_time(evt['start'])
            html += f'    <div style="padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px;"><strong>{time_str}</strong> &mdash; {evt["title"]}'
            if evt.get('location'):
                html += f' <span style="color: #888;">@ {evt["location"]}</span>'
            html += '</div>\n'
        html += '  </div>\n'

    # Personal inbox
    if emails:
        html += f'  <div style="{HEADER}">Personal Inbox ({len(emails)})</div>\n'
        html += f'  <div style="{CARD}">\n'
        for email in emails[:10]:
            from_short = email['from'].split('<')[0].strip().strip('"')
            html += f"""    <div style="padding: 8px 0; border-bottom: 1px solid #eee;">
      <div style="font-size: 13px; color: #666;">{from_short}</div>
      <div style="font-size: 14px; font-weight: 600; margin: 2px 0;">{email['subject']}</div>
      <div style="font-size: 12px; color: #888;">{email['snippet'][:120]}</div>
    </div>\n"""
        html += '  </div>\n'

    # Footer
    html += f"""
  <div style="{CARD} text-align: center;">
    <a href="{crm_data['sheet_url']}" style="display: inline-block; padding: 10px 24px; background: #1e293b; color: white; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">Open CRM Sheet</a>
  </div>

  <div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
    Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; Enriquez OS Personal Brand
  </div>
</div>

</body></html>"""

    return html


def cmd_evening_brief(args):
    print("Scanning CRM...")
    crm_data = scan_crm()
    print(f"  {crm_data['stats']['total']} leads, {crm_data['stats']['hot']} hot")

    print("Fetching personal calendar...")
    calendar = fetch_personal_calendar()
    print(f"  {len(calendar)} events")

    print("Fetching personal inbox...")
    emails = fetch_personal_gmail()
    print(f"  {len(emails)} emails")

    html = build_evening_html(crm_data, calendar, emails)

    action_count = crm_data['stats']['hot'] + len(crm_data.get('overdue', [])) + len(crm_data.get('due_today', []))
    subject = f"Evening Briefing {crm_data['date']} — {action_count} actions"

    if args.dry_run:
        preview_path = TMP_DIR / 'evening_briefing.html'
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(html)
        print(f"\nPreview saved to: {preview_path}")
        print(f"Subject: {subject}")
        return

    # Send email
    msg = MIMEMultipart('alternative')
    msg['to'] = BRIEFING_TO
    msg['from'] = BRIEFING_FROM
    msg['subject'] = subject
    msg.attach(MIMEText(html, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = get_gmail_service()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(f"\nEvening briefing sent to {BRIEFING_TO}")


# ============================================================
# draft — email drafting
# ============================================================

def cmd_draft(args):
    if not OUTPUT_FILE.exists():
        print("No cached data. Running scan...")
        scan_crm()

    data = json.loads(OUTPUT_FILE.read_text())
    target_tab = args.tab
    target_row = args.row

    # Find the lead
    lead = None
    for item in data.get('action_items', []):
        if item['tab'] == target_tab and item['row_num'] == target_row:
            lead = item
            break

    if not lead:
        # Check all leads (including uncalled)
        crm_data = scan_crm()
        for item in crm_data.get('action_items', []):
            if item['tab'] == target_tab and item['row_num'] == target_row:
                lead = item
                break

    if not lead:
        print(f"No lead found at {target_tab} row {target_row}")
        return

    # Load template
    template_path = TEMPLATE_DIR / 'outreach.txt'
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return

    template = template_path.read_text()

    # Select opener based on outcome
    outcome = lead.get('call_outcome', '')
    first_name = lead.get('decision_maker', '').split()[0] if lead.get('decision_maker') else 'there'

    if outcome == 'Warm Interest':
        # Personalise based on notes
        personal = lead.get('personal_details', [])
        personal_hook = ''
        if personal:
            detail = personal[0]
            personal_hook = f" Hope the {detail.split('likes')[-1].strip()} is going well!"
        opener = f"{first_name},\n\nGreat chatting with you.{personal_hook} As we discussed:"
    elif outcome == 'Asked For Email':
        opener = f"{first_name},\n\nAs promised from our call — here's what I do."
    else:
        opener = f"{first_name},\n\nI was going through your websites and loved the projects."

    # Fill template
    email_text = template.replace('[opener]', opener)
    email_text = email_text.replace('[businessName]', lead.get('business_name', ''))

    print(f"To: {lead.get('email', '(no email)')}")
    print(f"Re: {lead['business_name']} ({lead['decision_maker']})")
    print(f"Outcome: {outcome}")
    print(f"\n{'='*50}\n")
    print(email_text)
    print(f"\n{'='*50}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Personal Brand CRM Manager')
    sub = parser.add_subparsers(dest='command')

    p_clean = sub.add_parser('clean', help='One-time sheet cleanup')
    p_clean.add_argument('--dry-run', action='store_true', help='Preview changes only')

    p_brief = sub.add_parser('evening-brief', help='Send evening briefing email')
    p_brief.add_argument('--dry-run', action='store_true', help='Save HTML preview, don\'t send')

    p_cleanup = sub.add_parser('cleanup', help='Post-calling CRM normalisation')
    p_cleanup.add_argument('--dry-run', action='store_true', help='Preview changes only')

    p_draft = sub.add_parser('draft', help='Draft outreach email for a lead')
    p_draft.add_argument('--row', type=int, required=True, help='Sheet row number')
    p_draft.add_argument('--tab', required=True, help='Tab name')

    sub.add_parser('review', help='Print terminal summary')

    args = parser.parse_args()

    if args.command == 'clean':
        cmd_clean(args)
    elif args.command == 'evening-brief':
        cmd_evening_brief(args)
    elif args.command == 'cleanup':
        cmd_cleanup(args)
    elif args.command == 'draft':
        cmd_draft(args)
    elif args.command == 'review':
        cmd_review(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
