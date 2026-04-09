"""
Kanban CRM — local web UI for Allen's personal brand CRM.

Reads/writes to the same Google Sheet as personal_crm.py.
Drag-and-drop cards between columns to move leads between stages.

Usage:
    pip install flask
    python3 tools/crm_kanban/app.py
    # Opens at http://localhost:5001
"""

import json
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Import shared code from personal_crm.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from personal_crm import (
    ALL_TABS,
    ACTION_OUTCOMES,
    CALLBACK_OUTCOMES,
    DEAD_OUTCOMES,
    DROPDOWN_VALUES,
    HOT_OUTCOMES,
    SPREADSHEET_ID,
    TAB_GROUPS,
    TARGET_HEADERS,
    classify_lead,
    get_cell,
    get_sheets_service,
    load_token,
    move_rows_between_tabs,
    parse_row,
)

app = Flask(__name__)

# --- In-memory cache ---
_cache = {'data': None, 'time': 0, 'ttl': 30}

STAGE_ORDER = [
    'call_queue', 'no_answer', 'not_interested', 'callbacks',
    'send_email', 'awaiting_reply', 'late_follow_up', 'warm_interest',
    'meeting_booked',
]
STAGE_LABELS = {
    'call_queue': 'Call Queue',
    'no_answer': 'No Answer',
    'not_interested': 'Not Interested',
    'callbacks': 'Callbacks',
    'send_email': 'Send Email',
    'awaiting_reply': 'Awaiting Reply',
    'late_follow_up': 'Late Follow Up',
    'warm_interest': 'Warm Interest',
    'meeting_booked': 'Meeting Booked',
}

# Map call outcomes to Kanban stages
OUTCOME_TO_STAGE = {
    'New / No Label': 'call_queue',
    'No Answer 1': 'no_answer',
    'No Answer 2': 'no_answer',
    'No Answer 3': 'no_answer',
    'No Answer 4': 'no_answer',
    'No Answer 5': 'no_answer',
    'Call Back': 'callbacks',
    'Late Follow Up': 'late_follow_up',
    'Asked For Email': 'send_email',      # overridden to awaiting_reply if date_emailed is set
    'Warm Interest': 'warm_interest',
    'Meeting Booked': 'meeting_booked',
    'Not Interested - Convo': 'not_interested',
    'Not Interested - No Convo': 'not_interested',
    'Invalid Number': 'not_interested',
    'Hung Up - No Convo': 'not_interested',
}

# Reverse: when dragging to a stage, what outcome to set
STAGE_TO_DEFAULT_OUTCOME = {
    'call_queue': None,                    # keep existing outcome
    'no_answer': 'No Answer 1',
    'not_interested': 'Not Interested - Convo',
    'callbacks': 'Call Back',
    'send_email': 'Asked For Email',
    'awaiting_reply': 'Asked For Email',   # + set date_emailed
    'late_follow_up': 'Late Follow Up',
    'warm_interest': 'Warm Interest',
    'meeting_booked': 'Meeting Booked',
}


def get_sheets_meta():
    """Get spreadsheet metadata (tab names → sheet IDs)."""
    service = get_sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    return {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}


def stage_for_lead(lead):
    """Determine Kanban stage from lead's outcome + email status."""
    outcome = lead.get('call_outcome', '') or 'New / No Label'
    stage = OUTCOME_TO_STAGE.get(outcome, 'call_queue')
    # Asked For Email + already emailed → Awaiting Reply
    if stage == 'send_email' and lead.get('date_emailed', '').strip():
        stage = 'awaiting_reply'
    return stage


def load_board(group='paint'):
    """Load all leads from Sheet, grouped by Kanban column (outcome-based)."""
    now = time.time()
    if _cache['data'] and _cache.get('group') == group and (now - _cache['time']) < _cache['ttl']:
        return _cache['data']

    service = get_sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_tabs = {s['properties']['title'] for s in meta['sheets']}

    # Determine which tabs to read
    if group == 'all':
        tabs = ALL_TABS
    else:
        tabs = list(TAB_GROUPS.get(group, TAB_GROUPS['paint']).values())

    columns = {stage: [] for stage in STAGE_ORDER}
    stats = {'total': 0, 'hot': 0, 'callbacks_due': 0, 'emails_pending': 0}

    for tab in tabs:
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
            if not lead:
                continue

            lead_type, priority = classify_lead(lead)
            lead['type'] = lead_type
            lead['priority'] = priority

            # Add enrichment fields
            lead['city'] = get_cell(row, col_map, 'City')
            lead['service_areas'] = get_cell(row, col_map, 'Service Areas')
            lead['social_media'] = get_cell(row, col_map, 'Social Media')
            lead['linkedin'] = get_cell(row, col_map, 'LinkedIn')
            lead['bbb_rating'] = get_cell(row, col_map, 'BBB Rating')
            lead['personal_hook'] = get_cell(row, col_map, 'Personal Hook')
            lead['phone2'] = get_cell(row, col_map, 'Phone 2')

            # Store raw row data for move operations
            padded = list(row) + [''] * (len(headers) - len(row))
            lead['_row_data'] = padded[:len(TARGET_HEADERS)]

            # Assign to Kanban column by outcome, not by Sheet tab
            stage = stage_for_lead(lead)
            columns[stage].append(lead)

            stats['total'] += 1
            if lead['call_outcome'] in HOT_OUTCOMES:
                stats['hot'] += 1
            if lead_type == 'callback' and priority in ('HIGH', 'URGENT'):
                stats['callbacks_due'] += 1
            if lead_type == 'email_needed':
                stats['emails_pending'] += 1

    # Sort each column: most recently called first, then by priority
    from datetime import datetime
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}

    def sort_key(lead):
        # Parse date_called (format: "7 April") — most recent first
        dc = (lead.get('date_called', '') or '').strip()
        if dc:
            try:
                dt = datetime.strptime(f"{dc} {datetime.now().year}", '%d %B %Y')
                has_date = 0   # dated leads first
                date_score = -dt.timestamp()  # newer = smaller
            except (ValueError, TypeError):
                has_date = 1
                date_score = 0
        else:
            has_date = 1   # no date → after dated leads
            date_score = 0
        return (has_date, date_score, priority_order.get(lead['priority'], 4))

    for stage in columns:
        columns[stage].sort(key=sort_key)

    board = {'columns': columns, 'stats': stats}
    _cache['data'] = board
    _cache['time'] = now
    _cache['group'] = group
    return board


def invalidate_cache():
    _cache['data'] = None


# --- Routes ---

@app.route('/')
def index():
    group = request.args.get('group', 'paint')
    board = load_board(group)
    return render_template(
        'index.html',
        columns=board['columns'],
        stats=board['stats'],
        stage_order=STAGE_ORDER,
        stage_labels=STAGE_LABELS,
        group=group,
        dropdown_values=DROPDOWN_VALUES,
        hot_outcomes=list(HOT_OUTCOMES),
        action_outcomes=list(ACTION_OUTCOMES),
        callback_outcomes=list(CALLBACK_OUTCOMES),
        dead_outcomes=list(DEAD_OUTCOMES),
    )


@app.route('/api/leads')
def api_leads():
    group = request.args.get('group', 'paint')
    board = load_board(group)
    # Strip _row_data from JSON response (it's large)
    clean = {}
    for stage, leads in board['columns'].items():
        clean[stage] = [{k: v for k, v in l.items() if k != '_row_data'} for l in leads]
    return jsonify({'columns': clean, 'stats': board['stats']})


@app.route('/api/move-card', methods=['POST'])
def api_move_card():
    """Handle drag-and-drop: update the lead's outcome (and optionally move Sheet tabs)."""
    data = request.json
    tab = data.get('tab')
    row_num = data.get('row_num')
    target_stage = data.get('target_stage')
    row_data = data.get('row_data')

    if not tab or not row_num or not target_stage:
        return jsonify({'ok': False, 'error': 'Missing fields'}), 400

    try:
        service = get_sheets_service()

        # Read headers to find column positions
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!1:1"
        ).execute()
        headers = result.get('values', [[]])[0]
        col_map = {h: i for i, h in enumerate(headers)}

        # Update the Call Outcome field based on target stage
        new_outcome = STAGE_TO_DEFAULT_OUTCOME.get(target_stage)
        batch_data = []

        if new_outcome and 'Call Outcome' in col_map:
            col_idx = col_map['Call Outcome']
            col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
            batch_data.append({
                'range': f"'{tab}'!{col_letter}{row_num}",
                'values': [[new_outcome]],
            })

        # If moving to "Awaiting Reply", set Date Emailed to today
        if target_stage == 'awaiting_reply' and 'Date Emailed' in col_map:
            from datetime import datetime
            col_idx = col_map['Date Emailed']
            col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
            batch_data.append({
                'range': f"'{tab}'!{col_letter}{row_num}",
                'values': [[datetime.now().strftime('%d %B')]],
            })

        if batch_data:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'RAW', 'data': batch_data},
            ).execute()

        # Also move to the correct Sheet tab if needed
        from personal_crm import group_from_tab, determine_target_tab
        group_key = group_from_tab(tab)
        if group_key and row_data:
            # Update the outcome in row_data before determining target tab
            if new_outcome and 'Call Outcome' in col_map:
                idx = col_map['Call Outcome']
                if idx < len(row_data):
                    row_data[idx] = new_outcome
            if target_stage == 'awaiting_reply' and 'Date Emailed' in col_map:
                idx = col_map['Date Emailed']
                if idx < len(row_data):
                    from datetime import datetime as dt
                    row_data[idx] = dt.now().strftime('%d %B')

            # Build a minimal lead dict for determine_target_tab
            temp_lead = {
                'call_outcome': new_outcome or data.get('current_outcome', ''),
                'date_emailed': row_data[col_map['Date Emailed']] if 'Date Emailed' in col_map and col_map['Date Emailed'] < len(row_data) else '',
            }
            target_tab = determine_target_tab(temp_lead, group_key)
            if target_tab != tab:
                sheets_meta = get_sheets_meta()
                moves = {tab: [(row_data, target_tab)]}
                move_rows_between_tabs(service, moves, sheets_meta)

        invalidate_cache()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/update-card', methods=['POST'])
def api_update_card():
    data = request.json
    tab = data.get('tab')
    row_num = data.get('row_num')
    updates = data.get('updates', {})

    if not tab or not row_num or not updates:
        return jsonify({'ok': False, 'error': 'Missing fields'}), 400

    try:
        service = get_sheets_service()
        # Read headers to find column letters
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!1:1"
        ).execute()
        headers = result.get('values', [[]])[0]
        col_map = {h: i for i, h in enumerate(headers)}

        # Handle header aliases
        alias = {'Decision Maker': 'Owner Name / DM'}
        batch_data = []
        for field, value in updates.items():
            key = field if field in col_map else alias.get(field, field)
            if key in col_map:
                col_idx = col_map[key]
                col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
                batch_data.append({
                    'range': f"'{tab}'!{col_letter}{row_num}",
                    'values': [[value]],
                })

        if batch_data:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'valueInputOption': 'RAW', 'data': batch_data},
            ).execute()

        invalidate_cache()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("CRM Kanban Board → http://localhost:5001")
    app.run(port=5001, debug=True)
