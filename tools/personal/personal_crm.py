"""
Personal Brand CRM Manager.

Manages Allen's Google Sheets CRM for cold-calling painting companies in Charlotte NC.

Subcommands:
    clean          One-time sheet cleanup (reorder cols, format, dedupe, normalise)
    evening-brief  Send evening briefing email (priority call list + personal calendar/inbox)
    cleanup        Post-calling CRM normalisation (automated at 12:30 AM via launchd)
    draft          Draft outreach email for a specific lead
    review         Print terminal summary of CRM priorities
    update-note    Update any field for a specific lead (used by follow-up agent)

Usage:
    python3 tools/personal_crm.py clean --dry-run
    python3 tools/personal_crm.py clean
    python3 tools/personal_crm.py evening-brief --dry-run
    python3 tools/personal_crm.py evening-brief
    python3 tools/personal_crm.py cleanup --dry-run
    python3 tools/personal_crm.py cleanup
    python3 tools/personal_crm.py draft --row 3 --tab "Painting Companies"
    python3 tools/personal_crm.py review
    python3 tools/personal_crm.py update-note --tab "Paint | Emails Sent" --row 5 --field "Date Emailed" --value "2026-04-10"

Requires:
    projects/personal/token_personal_ai.pickle: Google OAuth token with Sheets + Gmail + Calendar
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
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'personal_crm.json'
CLEANUP_LOG = TMP_DIR / 'personal_crm_cleanup.log'
TEMPLATE_DIR = BASE_DIR / 'projects' / 'personal' / 'templates' / 'email'

SPREADSHEET_ID = '1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8'

# --- Tab structure ---
TAB_GROUPS = {
    'paint': {
        'call_queue':    'Paint | Call Queue',
        'warm_interest': 'Paint | Warm Interest',
        'callbacks':     'Paint | Callbacks',
        'emails_sent':   'Paint | Emails Sent',
        'not_interested':'Paint | Not Interested',
    },
    'other': {
        'call_queue':    'Other | Call Queue',
        'warm_interest': 'Other | Warm Interest',
        'callbacks':     'Other | Callbacks',
        'emails_sent':   'Other | Emails Sent',
        'not_interested':'Other | Not Interested',
    },
}
ALL_TABS = [tab for group in TAB_GROUPS.values() for tab in group.values()]
OLD_TAB_TO_GROUP = {'Painting Companies': 'paint', 'Others': 'other'}
TABS = ['Painting Companies', 'Others']  # kept for migration only

BRIEFING_FROM = 'allenenriquez@gmail.com'
BRIEFING_TO = 'allenenriquez.ai@gmail.com'

# --- Column order ---
# A-I = Allen's primary view (zoomed in)
PRIMARY_COLS = [
    'Business Name', 'Decision Maker', 'Phone', 'Call Outcome', 'Notes',
    'Follow-up Date', 'Date Called', 'Email', 'Website',
]
SECONDARY_COLS = [
    'Date Emailed', 'City', 'Service Areas', 'Social Media', 'LinkedIn',
    'BBB Rating', 'Connected', 'Source', 'BBB URL', 'Phone 2',
]
TARGET_HEADERS = PRIMARY_COLS + SECONDARY_COLS

# --- Call outcome classifications ---
HOT_OUTCOMES = {'Warm Interest', 'Meeting Booked'}
ACTION_OUTCOMES = {'Asked For Email', 'Call Back', 'Late Follow Up'}
CALLBACK_OUTCOMES = {'No Answer 1', 'No Answer 2', 'No Answer 3', 'No Answer 4', 'No Answer 5'}
DEAD_OUTCOMES = {'Not Interested - Convo', 'Invalid Number', 'Hung Up - No Convo'}

DROPDOWN_VALUES = [
    'New / No Label', 'No Answer 1', 'No Answer 2', 'No Answer 3',
    'No Answer 4', 'No Answer 5', 'Hung Up - No Convo',
    'Not Interested - Convo', 'Invalid Number', 'Call Back',
    'Asked For Email', 'Late Follow Up', 'Warm Interest', 'Meeting Booked',
]

# Formatting colours (RGB 0-1)
COLOUR_HEADER_BG = {'red': 0.118, 'green': 0.161, 'blue': 0.231}  # #1e293b
COLOUR_ALT_ROW = {'red': 0.973, 'green': 0.98, 'blue': 0.984}    # #f8f9fa
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
            r'(?:call\s*back|follow\s*up)\s+in\s+(\d+\s+weeks?)',
            r'(?:call\s*back|follow\s*up)\s+in\s+(\d+\s+days?)',
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


def next_weekday(date):
    """If date falls on Sat/Sun, push to next Monday."""
    if date.weekday() == 5:  # Saturday
        return date + timedelta(days=2)
    if date.weekday() == 6:  # Sunday
        return date + timedelta(days=1)
    return date


def resolve_relative_date(raw):
    """Try to resolve a relative date string to YYYY-MM-DD. Returns '' if can't."""
    today = datetime.now().date()

    # "N weeks" → N weeks from today, land on a weekday
    m = re.match(r'^(\d+)\s+weeks?$', raw.strip())
    if m:
        return next_weekday(today + timedelta(weeks=int(m.group(1)))).isoformat()

    # "N days" → N days from today, land on a weekday
    m = re.match(r'^(\d+)\s+days?$', raw.strip())
    if m:
        return next_weekday(today + timedelta(days=int(m.group(1)))).isoformat()

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
        'phone2': get_cell(row, col_map, 'Phone 2'),
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


def determine_target_tab(lead, group_key):
    """Return the tab name a lead belongs in based on outcome and email status."""
    outcome = lead.get('call_outcome', '')
    date_emailed = lead.get('date_emailed', '')

    if outcome in HOT_OUTCOMES:
        return TAB_GROUPS[group_key]['warm_interest']
    if outcome in DEAD_OUTCOMES:
        return TAB_GROUPS[group_key]['not_interested']
    if outcome in ('Call Back', 'Late Follow Up'):
        return TAB_GROUPS[group_key]['callbacks']
    if outcome == 'No Answer 5':
        return TAB_GROUPS[group_key]['callbacks']
    if outcome == 'Asked For Email' and date_emailed:
        return TAB_GROUPS[group_key]['emails_sent']
    # Everything else: uncalled, No Answer 1-4, Asked For Email (not yet emailed)
    return TAB_GROUPS[group_key]['call_queue']


def group_from_tab(tab_name):
    """Return group key ('paint'/'other') for a given tab name."""
    for group_key, tabs in TAB_GROUPS.items():
        if tab_name in tabs.values():
            return group_key
    return OLD_TAB_TO_GROUP.get(tab_name)


# ============================================================
# CRM scan — reads sheet, builds JSON
# ============================================================

def scan_crm():
    """Read all tabs, parse all rows, return structured data."""
    service = get_sheets_service()
    all_leads = []

    # Try new tabs first; fall back to old flat tabs if new ones don't exist yet
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_tabs = {s['properties']['title'] for s in meta['sheets']}
    tabs_to_scan = ALL_TABS if any(t in existing_tabs for t in ALL_TABS) else TABS

    for tab in tabs_to_scan:
        if tab not in existing_tabs:
            continue
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

    # Deduplicate: same business name + phone = same lead
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    dedup = {}
    for lead in all_leads:
        key = (lead['business_name'].lower().strip(), lead['phone'].strip())
        if key in dedup:
            existing = dedup[key]
            # Keep the higher-priority version as the base
            if priority_order.get(lead['priority'], 4) < priority_order.get(existing['priority'], 4):
                # New lead is higher priority — swap, merge notes from old into new
                lead['notes'] = (lead.get('notes', '') + '\n---\n' + existing.get('notes', '')).strip()
                lead['notes_truncated'] = lead['notes'][:200] if lead['notes'] else ''
                lead['todos'] = list(dict.fromkeys(lead.get('todos', []) + existing.get('todos', [])))
                lead['personal_details'] = list(dict.fromkeys(lead.get('personal_details', []) + existing.get('personal_details', [])))
                if not lead.get('follow_up_date') and existing.get('follow_up_date'):
                    lead['follow_up_date'] = existing['follow_up_date']
                if not lead.get('email') and existing.get('email'):
                    lead['email'] = existing['email']
                dedup[key] = lead
            else:
                # Existing is higher priority — merge notes from new into existing
                existing['notes'] = (existing.get('notes', '') + '\n---\n' + lead.get('notes', '')).strip()
                existing['notes_truncated'] = existing['notes'][:200] if existing['notes'] else ''
                existing['todos'] = list(dict.fromkeys(existing.get('todos', []) + lead.get('todos', [])))
                existing['personal_details'] = list(dict.fromkeys(existing.get('personal_details', []) + lead.get('personal_details', [])))
                if not existing.get('follow_up_date') and lead.get('follow_up_date'):
                    existing['follow_up_date'] = lead['follow_up_date']
                if not existing.get('email') and lead.get('email'):
                    existing['email'] = lead['email']
        else:
            dedup[key] = lead
    all_leads = list(dedup.values())

    # Sort by priority
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

    # Clear existing banding before adding (prevents duplicate error on re-run)
    try:
        sheet_meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for s in sheet_meta['sheets']:
            if s['properties']['sheetId'] == sheet_id:
                for band in s.get('bandedRanges', []):
                    requests.append({'deleteBanding': {'bandedRangeId': band['bandedRangeId']}})
                break
    except Exception:
        pass

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

    # No conditional formatting — Allen manages chip colours manually in Sheets UI
    outcome_col = 3  # Call Outcome is always column D after reorder

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

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={'requests': requests}
    ).execute()
    print(f"  [{tab}] Formatting applied")


# ============================================================
# reorganize — one-time migration to status-based tabs
# ============================================================

def cmd_reorganize(args):
    """Create status-based tabs and move rows from flat tabs."""
    service = get_sheets_service()

    # Read existing flat tabs
    buckets = {tab: [] for tab in ALL_TABS}
    total_rows = 0

    for old_tab in TABS:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{old_tab}'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) < 2:
            continue

        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}
        group_key = OLD_TAB_TO_GROUP[old_tab]

        for row in rows[1:]:
            lead = parse_row(row, col_map, old_tab, 0)
            if not lead:
                continue
            # Pad row to full header width
            while len(row) < len(headers):
                row.append('')
            # Reorder columns to TARGET_HEADERS
            reordered = []
            for col_name in TARGET_HEADERS:
                idx = col_map.get(col_name)
                reordered.append(row[idx] if idx is not None and idx < len(row) else '')
            target = determine_target_tab(lead, group_key)
            # Auto-set follow-up for No Answer 5 without one
            if lead['call_outcome'] == 'No Answer 5' and not lead['follow_up_date']:
                fu_date = (datetime.now() + timedelta(weeks=3)).date().isoformat()
                fu_idx = TARGET_HEADERS.index('Follow-up Date')
                reordered[fu_idx] = fu_date
            buckets[target].append(reordered)
            total_rows += 1

    # Print summary
    print(f"\nMigration plan ({total_rows} total rows):")
    for tab, rows in buckets.items():
        if rows:
            print(f"  {tab}: {len(rows)} leads")

    if args.dry_run:
        print(f"\nDry run — no changes made. Run without --dry-run to apply.")
        return

    # Get existing sheet metadata
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}

    # Create new tabs
    add_requests = []
    for tab_name in ALL_TABS:
        if tab_name not in existing:
            add_requests.append({'addSheet': {'properties': {'title': tab_name}}})
    if add_requests:
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body={'requests': add_requests}
        ).execute()
        # Update existing map with newly created sheets
        for reply in resp.get('replies', []):
            if 'addSheet' in reply:
                props = reply['addSheet']['properties']
                existing[props['title']] = props['sheetId']
        print(f"  Created {len(add_requests)} new tabs")

    # Write data to each new tab
    for tab_name in ALL_TABS:
        data = [TARGET_HEADERS] + buckets.get(tab_name, [])
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'"
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A1",
            valueInputOption='RAW',
            body={'values': data}
        ).execute()
        print(f"  [{tab_name}] Wrote {len(data) - 1} rows")

    # Apply formatting to each tab
    for tab_name in ALL_TABS:
        sheet_id = existing[tab_name]
        apply_formatting(service, sheet_id, tab_name)

    # Hide old flat tabs (don't delete for safety)
    hide_requests = []
    for old_tab in TABS:
        if old_tab in existing:
            hide_requests.append({
                'updateSheetProperties': {
                    'properties': {'sheetId': existing[old_tab], 'hidden': True},
                    'fields': 'hidden'
                }
            })
    if hide_requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body={'requests': hide_requests}
        ).execute()
        print(f"  Hidden old tabs: {', '.join(TABS)}")

    # Refresh cache
    scan_crm()
    print(f"\nReorganization complete. {total_rows} leads distributed across {len(ALL_TABS)} tabs.")


def move_rows_between_tabs(service, moves, existing_sheets):
    """Execute row moves: append to destinations, rewrite sources with remaining rows.

    moves: dict of {source_tab: [(row_data, target_tab), ...]}
    existing_sheets: dict of {tab_name: sheet_id}
    """
    if not moves:
        return 0

    total_moved = 0
    # Group appends by destination
    appends = {}  # {target_tab: [row_data, ...]}
    for source_tab, row_moves in moves.items():
        for row_data, target_tab in row_moves:
            appends.setdefault(target_tab, []).append(row_data)
            total_moved += 1

    # Append rows to destination tabs
    for target_tab, rows in appends.items():
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{target_tab}'!A1",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': rows}
        ).execute()

    # Rewrite source tabs with remaining rows only
    for source_tab, row_moves in moves.items():
        moved_indices = set()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{source_tab}'"
        ).execute()
        all_rows = result.get('values', [])
        if not all_rows:
            continue
        headers = all_rows[0]

        # Match moved rows by content (row_data matches)
        moved_set = set()
        for row_data, _ in row_moves:
            moved_set.add(tuple(row_data))

        remaining = [headers]
        for row in all_rows[1:]:
            # Pad row for comparison
            padded = list(row) + [''] * (len(headers) - len(row))
            if tuple(padded[:len(TARGET_HEADERS)]) not in moved_set:
                remaining.append(row)
            else:
                # Remove from set so duplicates are handled correctly
                moved_set.discard(tuple(padded[:len(TARGET_HEADERS)]))

        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID, range=f"'{source_tab}'"
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{source_tab}'!A1",
            valueInputOption='RAW',
            body={'values': remaining}
        ).execute()

    return total_moved


# ============================================================
# cleanup — automated post-calling normalisation
# ============================================================

def cmd_cleanup(args):
    service = get_sheets_service()
    changes = []

    # Determine which tabs to scan
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    tabs_to_scan = [t for t in ALL_TABS if t in existing] or [t for t in TABS if t in existing]

    # Phase 1: Normalise empty outcomes and follow-up dates
    for tab in tabs_to_scan:
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

        if outcome_idx is None:
            continue

        batch_updates = []
        for i, row in enumerate(rows[1:], start=2):
            outcome = get_cell(row, col_map, 'Call Outcome')
            notes = get_cell(row, col_map, 'Notes')
            name = get_cell(row, col_map, 'Business Name')
            followup = get_cell(row, col_map, 'Follow-up Date') if followup_idx else ''

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

            if not followup and notes and followup_idx is not None:
                parsed = parse_notes(notes)
                if parsed['follow_up_date'] and parsed['follow_up_source'] == 'notes_parsed':
                    batch_updates.append({
                        'range': f"'{tab}'!{chr(65 + followup_idx)}{i}",
                        'values': [[parsed['follow_up_date']]]
                    })
                    changes.append(f"  [{tab}] Row {i} ({name}): follow-up → {parsed['follow_up_date']}")

        if args.dry_run:
            tab_changes = [c for c in changes if f'[{tab}]' in c]
            for c in tab_changes:
                print(c)
        elif batch_updates:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'RAW', 'data': batch_updates}
            ).execute()

    # Phase 2: Move rows to correct tabs (only if new tabs exist)
    uses_new_tabs = any(t in existing for t in ALL_TABS)
    moves = {}  # {source_tab: [(row_data, target_tab), ...]}
    move_log = []

    if uses_new_tabs:
        for tab in tabs_to_scan:
            gk = group_from_tab(tab)
            if not gk:
                continue
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
            ).execute()
            rows = result.get('values', [])
            if len(rows) < 2:
                continue
            headers = rows[0]
            col_map = {h: i for i, h in enumerate(headers)}

            for row in rows[1:]:
                lead = parse_row(row, col_map, tab, 0)
                if not lead:
                    continue
                target = determine_target_tab(lead, gk)
                if target != tab:
                    padded = list(row) + [''] * (len(headers) - len(row))
                    moves.setdefault(tab, []).append((padded[:len(TARGET_HEADERS)], target))
                    name = get_cell(row, col_map, 'Business Name')
                    move_log.append(f"  MOVE: {name} [{tab}] → [{target}]")

        if args.dry_run:
            for line in move_log:
                print(line)
        elif moves:
            moved = move_rows_between_tabs(service, moves, existing)
            changes.extend(move_log)
            print(f"  Moved {moved} rows between tabs")

    # Refresh cache
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

    # action_count computed after tonight/upcoming split below

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

    # Split leads into tonight (actionable now) vs upcoming (future follow-up)
    today_iso = datetime.now().date().isoformat()

    def actionable_tonight(lead):
        """No future follow-up date = call tonight."""
        return not lead.get('follow_up_date') or lead['follow_up_date'] <= today_iso

    # Tonight's calls: overdue + due today + hot/callback/no-answer with no future date
    tonight = []
    upcoming = []
    seen = set()

    # Overdue and due-today first (always tonight)
    for l in overdue + due_today:
        if id(l) not in seen:
            tonight.append(l)
            seen.add(id(l))

    # Hot leads — split by follow-up date
    for l in hot_leads:
        if id(l) not in seen:
            if actionable_tonight(l):
                tonight.append(l)
            else:
                upcoming.append(l)
            seen.add(id(l))

    # Callbacks, email-needed, follow-ups — split by date (no-answers are "call whenever", skip them)
    for l in action_items:
        if id(l) not in seen and l['type'] in ('callback', 'email_needed', 'follow_up'):
            if actionable_tonight(l):
                tonight.append(l)
            else:
                upcoming.append(l)
            seen.add(id(l))

    def render_lead_card(item, card_style, icon, badge=''):
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

        return f"""  <div style="{card_style}">
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

    # Tonight's Calls section
    if tonight:
        html += f'  <div style="{HEADER}">Tonight\'s Calls ({len(tonight)})</div>\n'
        for item in tonight:
            icon = priority_icons.get(item['priority'], '&#9898;')
            badge = ''
            if item in overdue:
                badge = '<span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">OVERDUE</span>'
            elif item in due_today:
                badge = '<span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">DUE TODAY</span>'
            card_style = AMBER if item['priority'] in ('URGENT', 'HIGH') else CARD
            html += render_lead_card(item, card_style, icon, badge)

    # Upcoming section (future follow-ups, de-emphasized)
    if upcoming:
        HEADER_MUTED = 'background: #64748b; color: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 16px; font-weight: 600;'
        html += f'  <div style="{HEADER_MUTED}">Upcoming ({len(upcoming)})</div>\n'
        for item in upcoming:
            icon = priority_icons.get(item['priority'], '&#9898;')
            html += render_lead_card(item, CARD, icon)

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

    # Personal inbox — split lead replies from other emails
    if emails:
        # Build set of known lead emails for matching
        lead_emails = set()
        for l in action_items + hot_leads:
            if l.get('email'):
                lead_emails.add(l['email'].lower().strip())

        lead_replies = []
        other_emails = []
        for email in emails:
            sender = email.get('from', '').lower()
            # Check if sender matches any lead email
            is_lead = any(addr in sender for addr in lead_emails if addr)
            if is_lead:
                lead_replies.append(email)
            else:
                other_emails.append(email)

        if lead_replies:
            html += f'  <div style="{HEADER}">Lead Replies ({len(lead_replies)})</div>\n'
            html += f'  <div style="{CARD} border-left: 4px solid #22c55e;">\n'
            for email in lead_replies:
                from_short = email['from'].split('<')[0].strip().strip('"')
                html += f"""    <div style="padding: 8px 0; border-bottom: 1px solid #eee;">
      <div style="font-size: 13px; color: #166534; font-weight: 600;">{from_short}</div>
      <div style="font-size: 14px; font-weight: 600; margin: 2px 0;">{email['subject']}</div>
      <div style="font-size: 12px; color: #888;">{email['snippet'][:120]}</div>
    </div>\n"""
            html += '  </div>\n'

        if other_emails:
            html += f'  <div style="{HEADER}">Personal Inbox ({len(other_emails)})</div>\n'
            html += f'  <div style="{CARD}">\n'
            for email in other_emails[:10]:
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


def promote_callbacks_to_queue(service, existing, dry_run=False):
    """Move callbacks with follow_up_date <= today into Call Queue tabs."""
    today = datetime.now().date().isoformat()
    moves = {}
    promoted = []

    for gk, tabs in TAB_GROUPS.items():
        cb_tab = tabs['callbacks']
        cq_tab = tabs['call_queue']
        if cb_tab not in existing:
            continue

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{cb_tab}'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) < 2:
            continue

        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}

        for row in rows[1:]:
            lead = parse_row(row, col_map, cb_tab, 0)
            if not lead:
                continue
            fu = lead.get('follow_up_date', '')
            if fu and fu <= today:
                padded = list(row) + [''] * (len(headers) - len(row))
                moves.setdefault(cb_tab, []).append((padded[:len(TARGET_HEADERS)], cq_tab))
                promoted.append(f"  PROMOTE: {lead['business_name']} → {cq_tab}")

    if promoted:
        for line in promoted:
            print(line)
        if not dry_run and moves:
            moved = move_rows_between_tabs(service, moves, existing)
            print(f"  Promoted {moved} callbacks to Call Queue")

    return len(promoted)


def cmd_evening_brief(args):
    # Promote due callbacks to Call Queue before building briefing
    service = get_sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    if any(t in existing for t in ALL_TABS):
        print("Checking callbacks due today...")
        promoted = promote_callbacks_to_queue(service, existing, dry_run=args.dry_run)
        if promoted:
            print(f"  {promoted} leads promoted to Call Queue")

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
# check_placeholders — detect unfilled [placeholder] patterns
# ============================================================

def check_placeholders(subject, body):
    """Check for unfilled [placeholder] patterns in email text."""
    import re
    pattern = r'\[[A-Za-z_][A-Za-z_0-9 ]*\]'
    found = []
    for label, text in [("Subject", subject), ("Body", body)]:
        matches = re.findall(pattern, text)
        if matches:
            found.extend([(label, m) for m in matches])
    return found


def send_outreach_email(to_email, subject, body):
    """Send a plain-text email via personal Gmail."""
    service = get_gmail_service()
    msg = MIMEMultipart()
    msg['to'] = to_email
    msg['from'] = 'Allen Enriquez <allenenriquez.ai@gmail.com>'
    msg['subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(f"\nEmail sent to {to_email}")


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
    business_name = lead.get('business_name', '')
    email_text = template.replace('[opener]', opener)
    email_text = email_text.replace('[businessName]', business_name)
    email_text = email_text.replace('[firstName]', first_name)

    # Extract subject from template (first line after SUBJECT:)
    subject = f"{first_name} — quick question about {business_name}"
    if email_text.startswith('SUBJECT:'):
        subject = email_text.split('\n')[0].replace('SUBJECT:', '').strip()
        email_text = '\n'.join(email_text.split('\n')[1:]).strip()

    # QA check
    placeholders = check_placeholders(subject, email_text)
    if placeholders:
        print("\n⚠️  WARNING: Unfilled placeholders detected!")
        for location, placeholder in placeholders:
            print(f"   {location}: {placeholder}")
        print("\nDraft (review and fill placeholders before sending):")
        print(f"\nSubject: {subject}")
        print(f"\n{email_text}")
        return

    to_email = lead.get('email', '')

    print(f"To: {to_email or '(no email)'}")
    print(f"Subject: {subject}")
    print(f"Outcome: {outcome}")
    print(f"\n{'='*50}\n")
    print(email_text)
    print(f"\n{'='*50}")

    # Send if --send flag is set
    if getattr(args, 'send', False):
        if not to_email:
            print("\n⚠️  Cannot send — no email address for this lead.")
            return
        send_outreach_email(to_email, subject, email_text)
    else:
        print("\nDraft only. Add --send to send.")


# ============================================================
# update-note — update a field for a specific lead
# ============================================================

def cmd_update_note(args):
    service = get_sheets_service()
    tab = args.tab
    row_num = args.row
    field = args.field
    value = args.value

    # Read headers to find column
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!1:1"
    ).execute()
    headers = result.get('values', [[]])[0]
    col_map = {h: i for i, h in enumerate(headers)}

    if field not in col_map:
        print(f"ERROR: Field '{field}' not found in {tab}. Available: {', '.join(headers)}")
        sys.exit(1)

    col_index = col_map[field]
    col_letter = chr(ord('A') + col_index) if col_index < 26 else \
        chr(ord('A') + col_index // 26 - 1) + chr(ord('A') + col_index % 26)
    cell = f"'{tab}'!{col_letter}{row_num}"

    if args.dry_run:
        print(f"[DRY RUN] Would set {cell} = {value}")
        return

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=cell,
        valueInputOption='RAW', body={'values': [[value]]}
    ).execute()
    print(f"Updated {field} at {tab} row {row_num} → {value}")


# ============================================================
# dedupe-phone — remove duplicate phone numbers, merge rows
# ============================================================

OUTCOME_PRIORITY = {
    'Meeting Booked': 0,
    'Warm Interest': 1,
    'Asked For Email': 2,
    'Call Back': 3,
    'Late Follow Up': 4,
    'No Answer 5': 5,
    'No Answer 4': 6,
    'No Answer 3': 7,
    'No Answer 2': 8,
    'No Answer 1': 9,
    'Not Interested - Convo': 10,
    'Not Interested - No Convo': 11,
    'Invalid Number': 12,
    'New / No Label': 13,
    '': 14,
}


def normalise_phone(phone):
    """Strip non-digits for comparison."""
    return re.sub(r'\D', '', phone)


def merge_rows(winner, loser, headers):
    """Merge loser into winner: fill empty fields, combine notes."""
    merged = list(winner)
    # Extend to match header length
    while len(merged) < len(headers):
        merged.append('')

    loser_ext = list(loser)
    while len(loser_ext) < len(headers):
        loser_ext.append('')

    col_map = {h: i for i, h in enumerate(headers)}

    for h in headers:
        i = col_map[h]
        w_val = merged[i].strip() if i < len(merged) else ''
        l_val = loser_ext[i].strip() if i < len(loser_ext) else ''
        if not w_val and l_val:
            merged[i] = l_val

    # Merge Notes specially
    notes_i = col_map.get('Notes')
    if notes_i is not None:
        w_notes = merged[notes_i].strip()
        l_notes = loser_ext[notes_i].strip()
        if w_notes and l_notes and w_notes != l_notes:
            merged[notes_i] = w_notes + '\n___\n' + l_notes

    return merged


def cmd_dedupe_phone(args):
    service = get_sheets_service()
    tab = 'Painting Companies'

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
    ).execute()
    rows = result.get('values', [])
    if not rows:
        print("Sheet is empty.")
        return

    headers = rows[0]
    data = rows[1:]

    col_map = {h: i for i, h in enumerate(headers)}
    phone_i = col_map.get('Phone', 0)
    outcome_i = col_map.get('Call Outcome', -1)

    # Group rows by normalised phone
    groups = {}   # norm_phone -> list of rows
    no_phone = []

    for row in data:
        phone_raw = row[phone_i].strip() if phone_i < len(row) else ''
        norm = normalise_phone(phone_raw)
        if not norm:
            no_phone.append(row)
            continue
        groups.setdefault(norm, []).append(row)

    duplicates_found = sum(len(v) - 1 for v in groups.values() if len(v) > 1)
    if duplicates_found == 0:
        print("No duplicate phone numbers found.")
        return

    print(f"Found {duplicates_found} duplicate row(s) to merge.")

    # Merge each group
    merged_rows = []
    for norm, group in groups.items():
        if len(group) == 1:
            merged_rows.append(group[0])
            continue

        # Sort group: best outcome first
        def outcome_rank(row):
            outcome = row[outcome_i].strip() if outcome_i >= 0 and outcome_i < len(row) else ''
            return OUTCOME_PRIORITY.get(outcome, 14)

        group.sort(key=outcome_rank)
        winner = group[0]
        for loser in group[1:]:
            winner = merge_rows(winner, loser, headers)
        merged_rows.append(winner)

    # Re-sort: called leads on top (same as clean command)
    def sort_key(row):
        outcome = row[outcome_i].strip() if outcome_i >= 0 and outcome_i < len(row) else ''
        if outcome in HOT_OUTCOMES:
            return 0
        if outcome in ACTION_OUTCOMES:
            return 1
        if outcome in CALLBACK_OUTCOMES:
            return 2
        if outcome in DEAD_OUTCOMES:
            return 4
        return 3

    def has_outcome(row):
        return outcome_i >= 0 and outcome_i < len(row) and row[outcome_i].strip()

    called = [r for r in merged_rows if has_outcome(r)]
    uncalled_merged = [r for r in merged_rows if not has_outcome(r)]
    called_no_phone = [r for r in no_phone if has_outcome(r)]
    uncalled_no_phone = [r for r in no_phone if not has_outcome(r)]

    called.sort(key=sort_key)
    called_no_phone.sort(key=sort_key)

    final_rows = [headers] + called + called_no_phone + uncalled_merged + uncalled_no_phone

    total_before = len(data)
    total_after = len(final_rows) - 1

    if args.dry_run:
        print(f"[DRY RUN] Would reduce {total_before} rows → {total_after} rows ({duplicates_found} removed).")
        for norm, group in groups.items():
            if len(group) > 1:
                names = [g[col_map.get('Business Name', 0)] if col_map.get('Business Name', 0) < len(g) else '?' for g in group]
                print(f"  Phone {norm}: {' + '.join(names)}")
        return

    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
        valueInputOption='RAW', body={'values': final_rows}
    ).execute()

    print(f"Done. {total_before} rows → {total_after} rows ({duplicates_found} duplicates merged).")

    for norm, group in groups.items():
        if len(group) > 1:
            names = [g[col_map.get('Business Name', 0)] if col_map.get('Business Name', 0) < len(g) else '?' for g in group]
            print(f"  Merged: {' + '.join(names)}")


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
    p_draft.add_argument('--send', action='store_true', help='Send the email after drafting (default: draft only)')

    sub.add_parser('review', help='Print terminal summary')

    p_dedupe = sub.add_parser('dedupe-phone', help='Remove duplicate phone numbers, merge rows')
    p_dedupe.add_argument('--dry-run', action='store_true', help='Preview changes only')

    p_reorg = sub.add_parser('reorganize', help='One-time migration to status-based tabs')
    p_reorg.add_argument('--dry-run', action='store_true', help='Preview tab assignments only')

    p_update = sub.add_parser('update-note', help='Update a field for a specific lead')
    p_update.add_argument('--tab', required=True, help='Tab name')
    p_update.add_argument('--row', type=int, required=True, help='Sheet row number')
    p_update.add_argument('--field', default='Notes', help='Column name to update (default: Notes)')
    p_update.add_argument('--value', required=True, help='New value')
    p_update.add_argument('--dry-run', action='store_true', help='Preview only')

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
    elif args.command == 'dedupe-phone':
        cmd_dedupe_phone(args)
    elif args.command == 'reorganize':
        cmd_reorganize(args)
    elif args.command == 'update-note':
        cmd_update_note(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
