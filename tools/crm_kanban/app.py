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
from datetime import timedelta
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


_stats_cache = {'data': None, 'time': 0, 'ttl': 60}


@app.route('/api/outreach/detailed')
def api_outreach_detailed():
    """Rich call analytics for the cold calling feedback dashboard."""
    from collections import Counter
    from datetime import datetime

    try:
        now_ts = time.time()
        if _stats_cache['data'] and (now_ts - _stats_cache['time']) < _stats_cache['ttl']:
            return jsonify(_stats_cache['data'])

        service = get_sheets_service()
        now = datetime.now()
        today_label = f"{now.day} {now.strftime('%B')}"

        # Date labels for last 14 days
        date_labels = {}
        for d in range(14):
            dt = now - timedelta(days=d)
            date_labels[f"{dt.day} {dt.strftime('%B')}"] = dt.strftime('%Y-%m-%d')

        # Week (Sun–Sat)
        week_start = now - timedelta(days=(now.weekday() + 1) % 7)
        week_labels = set()
        for d in range(7):
            dt = week_start + timedelta(days=d)
            week_labels.add(f"{dt.day} {dt.strftime('%B')}")

        CONVO_OUTCOMES = {
            'Warm Interest', 'Meeting Booked', 'Call Back',
            'Asked For Email', 'Late Follow Up', 'Not Interested - Convo',
        }
        NO_ANSWER = {'No Answer 1', 'No Answer 2', 'No Answer 3', 'No Answer 4', 'No Answer 5'}

        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_tabs = {s['properties']['title'] for s in meta['sheets']}

        today_outcomes = []
        week_outcomes = []
        daily_data = {}
        total_called = 0
        total_uncalled = 0

        tabs_to_fetch = [t for t in ALL_TABS if t in existing_tabs]
        batch_res = service.spreadsheets().values().batchGet(
            spreadsheetId=SPREADSHEET_ID,
            ranges=[f"'{t}'" for t in tabs_to_fetch],
        ).execute()

        for tab, vr in zip(tabs_to_fetch, batch_res.get('valueRanges', [])):
            rows = vr.get('values', [])
            if not rows:
                continue
            headers = rows[0]
            col_map = {h: i for i, h in enumerate(headers)}

            for i, row in enumerate(rows[1:], start=2):
                lead = parse_row(row, col_map, tab, i)
                if not lead:
                    continue
                outcome = lead.get('call_outcome', '') or 'New / No Label'
                dc = (lead.get('date_called', '') or '').strip()

                if not dc or outcome == 'New / No Label':
                    total_uncalled += 1
                    continue

                total_called += 1
                if dc == today_label:
                    today_outcomes.append(outcome)
                if dc in week_labels:
                    week_outcomes.append(outcome)
                if dc in date_labels:
                    daily_data.setdefault(date_labels[dc], []).append(outcome)

        t_total = len(today_outcomes)
        t_convos = sum(1 for o in today_outcomes if o in CONVO_OUTCOMES)
        t_no_answer = sum(1 for o in today_outcomes if o in NO_ANSWER)
        t_hung_up = sum(1 for o in today_outcomes if o == 'Hung Up - No Convo')
        t_not_interested = sum(1 for o in today_outcomes if o == 'Not Interested - Convo')
        t_invalid = sum(1 for o in today_outcomes if o == 'Invalid Number')
        t_warm = sum(1 for o in today_outcomes if o in HOT_OUTCOMES)
        t_callback = sum(1 for o in today_outcomes if o == 'Call Back')
        t_email = sum(1 for o in today_outcomes if o == 'Asked For Email')
        t_meeting = sum(1 for o in today_outcomes if o == 'Meeting Booked')

        DAILY_GOAL = 100

        w_total = len(week_outcomes)
        w_convos = sum(1 for o in week_outcomes if o in CONVO_OUTCOMES)
        w_no_answer = sum(1 for o in week_outcomes if o in NO_ANSWER)
        w_hung_up = sum(1 for o in week_outcomes if o == 'Hung Up - No Convo')
        w_warm = sum(1 for o in week_outcomes if o in HOT_OUTCOMES)
        w_conv_rate = round(w_convos / w_total * 100) if w_total else 0

        conv_rate = round(t_convos / t_total * 100) if t_total else 0

        # 14-day trend
        trend = []
        for d in range(13, -1, -1):
            dt = now - timedelta(days=d)
            ds = dt.strftime('%Y-%m-%d')
            outs = daily_data.get(ds, [])
            day_total = len(outs)
            day_convos = sum(1 for o in outs if o in CONVO_OUTCOMES)
            trend.append({
                'date': ds, 'day': dt.strftime('%a'), 'short': dt.strftime('%d'),
                'calls': day_total, 'convos': day_convos,
                'rate': round(day_convos / day_total * 100) if day_total else 0,
            })

        # Streak
        streak = 0
        for d in range(1, 30):
            dt = now - timedelta(days=d)
            label = f"{dt.day} {dt.strftime('%B')}"
            if label in date_labels and date_labels[label] in daily_data:
                streak += 1
            else:
                break

        # --- Benchmarks for coaching ---
        past_7 = trend[-8:-1]
        past_14 = trend[:-1]
        past_7_calls = [d['calls'] for d in past_7 if d['calls'] > 0]
        avg_7 = round(sum(past_7_calls) / len(past_7_calls)) if past_7_calls else 0
        max_7 = max(past_7_calls) if past_7_calls else 0
        past_7_convos = sum(d['convos'] for d in past_7)
        past_7_total = sum(d['calls'] for d in past_7)
        avg_conv_rate_7 = round(past_7_convos / past_7_total * 100) if past_7_total else 0

        trend_3 = trend[-3:]
        is_declining_3 = (len(trend_3) == 3
                         and trend_3[0]['calls'] > trend_3[1]['calls'] > trend_3[2]['calls']
                         and trend_3[0]['calls'] > 10)

        warm_last_3_actual = sum(
            sum(1 for o in daily_data.get(d['date'], []) if o in HOT_OUTCOMES)
            for d in trend[-3:]
        )
        warm_last_10 = sum(
            sum(1 for o in daily_data.get(d['date'], []) if o in HOT_OUTCOMES)
            for d in trend[-11:-3] if d
        )

        hours_elapsed = max((now.hour + now.minute / 60) - 9, 0.1)
        hours_left = max(18 - (now.hour + now.minute / 60), 0)
        pace_per_hour = round(t_total / hours_elapsed, 1) if t_total > 0 and hours_elapsed > 0.5 else 0
        projected_eod = round(t_total + (pace_per_hour * hours_left)) if pace_per_hour > 0 else t_total

        # --- Next-level coaching nudges ---
        nudges = []

        if t_total == 0 and now.hour >= 10:
            if avg_7 > 20:
                nudges.append({'type': 'warning', 'text': f'Zero calls. It\'s {now.hour}:00. Your 7-day avg is {avg_7}. Phone up.'})
            else:
                nudges.append({'type': 'action', 'text': f'No calls yet at {now.hour}:00. First dial breaks inertia. Start now.'})
        elif t_total == 0 and now.hour < 10:
            nudges.append({'type': 'action', 'text': 'Fresh day. First call kicks it off.'})

        if is_declining_3:
            a, b, c = trend_3[0]['calls'], trend_3[1]['calls'], trend_3[2]['calls']
            nudges.append({'type': 'warning', 'text': f'3-day slide: {a} → {b} → {c}. Declining hard. What changed?'})

        if t_total > 0 and pace_per_hour > 0 and hours_left > 0.5:
            gap = DAILY_GOAL - t_total
            needed_pace = round(gap / hours_left, 1) if hours_left > 0 else 0
            if projected_eod < DAILY_GOAL * 0.6:
                nudges.append({'type': 'warning', 'text': f'Pace: {pace_per_hour}/hr. EOD projection: {projected_eod}. Need {needed_pace}/hr to hit 100. Big gap.'})
            elif projected_eod < DAILY_GOAL:
                nudges.append({'type': 'push', 'text': f'Pace: {pace_per_hour}/hr → {projected_eod} by EOD. Bump to {needed_pace}/hr for the goal.'})
            else:
                nudges.append({'type': 'win', 'text': f'On pace for {projected_eod} calls. Hold the rhythm.'})

        if t_total > 5 and avg_7 > 0:
            if t_total < avg_7 * 0.5 and now.hour >= 13:
                nudges.append({'type': 'warning', 'text': f'Today: {t_total}. 7-day avg: {avg_7}. You\'re half your pace. Why?'})
            elif t_total > max_7 and max_7 > 0:
                nudges.append({'type': 'win', 'text': f'New high: {t_total} calls beats your 7-day best ({max_7}). Lock this in.'})

        if t_total >= 10 and avg_conv_rate_7 > 0:
            if conv_rate > avg_conv_rate_7 * 1.3:
                nudges.append({'type': 'win', 'text': f'Conv rate {conv_rate}% vs {avg_conv_rate_7}% avg. Note what you changed today.'})
            elif conv_rate < avg_conv_rate_7 * 0.5 and t_total >= 15:
                nudges.append({'type': 'warning', 'text': f'Conv rate {conv_rate}% vs {avg_conv_rate_7}% avg. Opener is dying. Test a new one on next 10.'})

        if warm_last_3_actual == 0 and warm_last_10 > 3 and t_total > 0:
            nudges.append({'type': 'insight', 'text': f'Zero warm leads in 3 days ({warm_last_10} in days 4-10). Pitch drifted or list went cold.'})

        if t_no_answer > 5 and t_total > 0 and (t_no_answer / t_total) > 0.75:
            pct = round(t_no_answer / t_total * 100)
            nudges.append({'type': 'insight', 'text': f'{pct}% no-answers. Wrong hour or wrong list. Switch to 10-11am or 2-4pm window.'})

        if t_hung_up >= 4 and t_total > 0 and (t_hung_up / t_total) > 0.2:
            nudges.append({'type': 'warning', 'text': f'{t_hung_up} hang-ups. Opener too salesy. Lead with name + reason, not pitch.'})

        if t_invalid > 0 and t_total > 0 and (t_invalid / t_total) > 0.2:
            pct = round(t_invalid / t_total * 100)
            nudges.append({'type': 'insight', 'text': f'{pct}% invalid numbers. Lead source quality dropping. Check where these came from.'})

        if t_warm > 0:
            nudges.append({'type': 'win', 'text': f'{t_warm} warm lead{"s" if t_warm > 1 else ""} today. Follow up inside 24h — goes cold fast.'})

        if t_total >= DAILY_GOAL:
            nudges.append({'type': 'win', 'text': f'Goal hit: {t_total}. Now protect the warm leads. Draft follow-ups.'})

        if streak >= 3:
            nudges.append({'type': 'win', 'text': f'{streak}-day calling streak. Don\'t break it.'})

        payload = {
            'ok': True, 'goal': DAILY_GOAL,
            'today': {
                'total': t_total, 'no_answer': t_no_answer, 'hung_up': t_hung_up,
                'not_interested': t_not_interested, 'invalid': t_invalid,
                'callback': t_callback, 'email': t_email, 'warm': t_warm,
                'meeting': t_meeting, 'convos': t_convos, 'conv_rate': conv_rate,
            },
            'week': {
                'total': w_total, 'convos': w_convos, 'no_answer': w_no_answer,
                'hung_up': w_hung_up, 'warm': w_warm, 'conv_rate': w_conv_rate,
            },
            'alltime': {'called': total_called, 'uncalled': total_uncalled},
            'trend': trend, 'streak': streak,
            'best_day': max(trend[-7:], key=lambda x: x['calls']) if trend else None,
            'nudges': nudges,
        }
        _stats_cache['data'] = payload
        _stats_cache['time'] = time.time()
        return jsonify(payload)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("CRM Kanban Board → http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
