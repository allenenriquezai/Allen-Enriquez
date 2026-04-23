"""
Enriquez OS Dashboard — mobile-first personal productivity app.

Habit tracker + spend tracker + command center + Claude chat.
SQLite for instant reads/writes, background sync to Google Sheets.

Usage:
    python3 tools/dashboard/app.py
    # Opens at http://localhost:5002
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).parent.parent))
from personal_crm import get_sheets_service, load_token

# Dashboard sheet belongs to 006 account — use token_personal.pickle
_DASHBOARD_TOKEN = Path(__file__).parent.parent.parent / 'projects' / 'personal' / 'token_personal.pickle'

def _load_dashboard_creds():
    with open(_DASHBOARD_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(_DASHBOARD_TOKEN, 'wb') as f:
            pickle.dump(creds, f)
    return creds

import db
import sync

app = Flask(__name__)

# --- Config ---
SHEET_ID_FILE = Path(__file__).parent / 'SHEET_ID.txt'
DASHBOARD_SHEET_ID = None


def get_sheet_id():
    """Get or create the dashboard spreadsheet."""
    global DASHBOARD_SHEET_ID
    if DASHBOARD_SHEET_ID:
        return DASHBOARD_SHEET_ID

    if SHEET_ID_FILE.exists():
        DASHBOARD_SHEET_ID = SHEET_ID_FILE.read_text().strip()
        return DASHBOARD_SHEET_ID

    # Create new spreadsheet
    print("Creating Enriquez OS Dashboard spreadsheet...")
    service = get_sheets_service()
    spreadsheet = service.spreadsheets().create(body={
        'properties': {'title': 'Enriquez OS Dashboard'},
        'sheets': [
            {'properties': {'title': 'Checklist Config'}},
            {'properties': {'title': 'Checklist Log'}},
            {'properties': {'title': 'Spend Log'}},
        ],
    }).execute()

    DASHBOARD_SHEET_ID = spreadsheet['spreadsheetId']
    SHEET_ID_FILE.write_text(DASHBOARD_SHEET_ID)
    print(f"Sheet created: {DASHBOARD_SHEET_ID}")

    # Populate headers and default config
    _populate_defaults(service, DASHBOARD_SHEET_ID)
    return DASHBOARD_SHEET_ID


def _populate_defaults(service, sheet_id):
    """Populate Checklist Config with default items."""
    config_data = [
        ['Category', 'Item', 'Type', 'Order', 'Active'],
        # Personal Morning
        ['Personal Morning', 'Gratitude', 'check', '1', 'TRUE'],
        ['Personal Morning', 'Goal Review', 'check', '2', 'TRUE'],
        ['Personal Morning', 'Learn AI & Automation 1', 'check', '3', 'TRUE'],
        ['Personal Morning', 'Read (Pages)', 'count', '4', 'TRUE'],
        ['Personal Morning', 'Cardio', 'check', '5', 'TRUE'],
        # EPS
        ['EPS', 'Check Sent Quotes', 'check', '1', 'TRUE'],
        ['EPS', 'Check Follow Ups', 'check', '2', 'TRUE'],
        ['EPS', 'Sales Calls', 'check', '3', 'TRUE'],
        ['EPS', 'Discovery Calls', 'check', '4', 'TRUE'],
        ['EPS', 'Cold Calls / Outreach', 'check', '5', 'TRUE'],
        # Workout
        ['Workout', 'Pullups', 'count', '1', 'TRUE'],
        ['Workout', 'Dips', 'count', '2', 'TRUE'],
        ['Workout', 'Shoulder Press', 'count', '3', 'TRUE'],
        ['Workout', 'Pushups', 'count', '4', 'TRUE'],
        ['Workout', 'Squats', 'count', '5', 'TRUE'],
        # Family & Home
        ['Family & Home', 'Wife Time', 'check', '1', 'TRUE'],
        ['Family & Home', 'Bathe & Brush Marcus Aurelius', 'check', '2', 'TRUE'],
        ['Family & Home', 'Clean Office', 'check', '3', 'TRUE'],
        ['Family & Home', 'Clean Living Room', 'check', '4', 'TRUE'],
        ['Family & Home', 'Clean Bedroom', 'check', '5', 'TRUE'],
        # Personal Closing
        ['Personal Closing', 'Learn AI & Automation 2', 'check', '1', 'TRUE'],
        ['Personal Closing', 'Build Systems', 'check', '2', 'TRUE'],
        ['Personal Closing', 'Cold Outreach', 'check', '3', 'TRUE'],
        # Personal Brand (weekends only — replaces EPS)
        ['Personal Brand', 'Content Creation', 'check', '1', 'TRUE'],
        ['Personal Brand', 'Study AI Automation', 'check', '2', 'TRUE'],
    ]

    log_headers = [['Date', 'Item', 'Value', 'Timestamp']]
    spend_headers = [['Date', 'Category', 'Amount', 'Description', 'Timestamp']]

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            'valueInputOption': 'RAW',
            'data': [
                {'range': "'Checklist Config'!A1", 'values': config_data},
                {'range': "'Checklist Log'!A1", 'values': log_headers},
                {'range': "'Spend Log'!A1", 'values': spend_headers},
            ],
        },
    ).execute()
    print("Default data populated.")


def _svc():
    return build('sheets', 'v4', credentials=_load_dashboard_creds())


# ============================================================
# Checklist API
# ============================================================

def _load_config():
    """Load active checklist items grouped by category (from SQLite)."""
    return db.load_config()


def _load_log(date):
    """Load checklist completions for a date (from SQLite)."""
    return db.load_log(date)


# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    date = request.args.get('date', today_ph())
    config = _load_config()
    completions = _load_log(date)

    # Calculate stats
    total = sum(len(items) for items in config.values())
    done = 0
    for items in config.values():
        for item in items:
            val = completions.get(item['name'], '')
            if item['type'] == 'check' and val.upper() in ('TRUE', '1', 'YES'):
                done += 1
            elif item['type'] == 'count' and val and val != '0':
                done += 1
    pct = round(done / total * 100) if total else 0

    # Category order — weekends swap EPS for Personal Brand
    view_date = datetime.strptime(date, '%Y-%m-%d').date()
    is_weekend = view_date.weekday() in (5, 6)  # Sat=5, Sun=6
    if is_weekend:
        cat_order = ['Personal Morning', 'Personal Brand', 'Workout', 'Family & Home', 'Personal Closing']
    else:
        cat_order = ['Personal Morning', 'EPS', 'Workout', 'Family & Home', 'Personal Closing']
    categories = []
    for cat in cat_order:
        if cat not in config:
            continue
        items = config[cat]
        cat_done = 0
        cat_items = []
        for item in items:
            val = completions.get(item['name'], '')
            is_done = False
            if item['type'] == 'check':
                is_done = val.upper() in ('TRUE', '1', 'YES')
            elif item['type'] == 'count':
                is_done = bool(val and val != '0')
            if is_done:
                cat_done += 1
            cat_items.append({**item, 'value': val, 'done': is_done})
        categories.append({
            'name': cat,
            'checklist_items': cat_items,
            'done': cat_done,
            'total': len(items),
        })

    return render_template(
        'index.html',
        date=date,
        categories=categories,
        total=total,
        done=done,
        pct=pct,
    )


@app.route('/api/checklist/config')
def api_checklist_config():
    date = request.args.get('date', today_ph())
    config = _load_config()
    # Filter categories by weekday/weekend
    view_date = datetime.strptime(date, '%Y-%m-%d').date()
    is_weekend = view_date.weekday() in (5, 6)
    if is_weekend:
        config.pop('EPS', None)
    else:
        config.pop('Personal Brand', None)
    return jsonify({'ok': True, 'config': config})


@app.route('/api/checklist/<date>')
def api_checklist_date(date):
    completions = _load_log(date)
    return jsonify({'ok': True, 'completions': completions})


@app.route('/api/checklist/toggle', methods=['POST'])
def api_checklist_toggle():
    data = request.json
    date = data.get('date')
    item = data.get('item')
    value = data.get('value', 'TRUE')

    if not date or not item:
        return jsonify({'ok': False, 'error': 'Missing date or item'}), 400

    try:
        db.save_toggle(date, item, value)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/checklist/count', methods=['POST'])
def api_checklist_count():
    """Same as toggle but for count items."""
    return api_checklist_toggle()


@app.route('/api/checklist/weekly')
def api_checklist_weekly():
    """7-day summary ending at given date."""
    ref = request.args.get('end', today_ph())
    try:
        ref_date = datetime.strptime(ref, '%Y-%m-%d').date()
        # Always show Sun→Sat week containing the reference date
        # weekday(): Mon=0 ... Sun=6. We want Sunday as start.
        days_since_sunday = (ref_date.weekday() + 1) % 7
        start_date = ref_date - timedelta(days=days_since_sunday)
        end_date = start_date + timedelta(days=6)

        config = _load_config()

        # Build item sets for weekday vs weekend
        weekday_items = set()
        weekend_items = set()
        for cat, items in config.items():
            for item in items:
                if cat == 'EPS':
                    weekday_items.add(item['name'])
                elif cat == 'Personal Brand':
                    weekend_items.add(item['name'])
                else:
                    weekday_items.add(item['name'])
                    weekend_items.add(item['name'])

        # Load log entries for the date range from SQLite
        log_range = db.load_log_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        # Build per-day completion map
        daily = {}
        for day_key, completions in log_range.items():
            for item_name, val in completions.items():
                if val and val != '0' and val.upper() != 'FALSE':
                    daily.setdefault(day_key, set()).add(item_name)

        # Build summary — each day uses its own item set
        days = []
        d = start_date
        while d <= end_date:
            key = d.strftime('%Y-%m-%d')
            is_wknd = d.weekday() in (5, 6)
            day_items = weekend_items if is_wknd else weekday_items
            day_total = len(day_items)
            day_done_set = daily.get(key, set()) & day_items
            done = len(day_done_set)
            days.append({
                'date': key,
                'day': d.strftime('%a'),
                'done': done,
                'total': day_total,
                'pct': round(done / day_total * 100) if day_total else 0,
            })
            d += timedelta(days=1)

        # Missed items (items never completed this week, per their relevant days)
        all_done = set()
        for s in daily.values():
            all_done.update(s)
        all_items = weekday_items | weekend_items
        missed = list(all_items - all_done)

        # Streaks: consecutive days with >0 completions
        streak = 0
        for day in reversed(days):
            if day['done'] > 0:
                streak += 1
            else:
                break

        return jsonify({
            'ok': True,
            'days': days,
            'missed': missed,
            'streak': streak,
            'avg_pct': round(sum(d['pct'] for d in days) / len(days)) if days else 0,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Register blueprints (spend + command center)
# ============================================================

from routes_spend import spend_bp, init_spend
from routes_command import command_bp, init_command
from routes_brief import brief_bp, init_brief, warm_cache
from routes_deal import deal_bp
from routes_ops import ops_bp
from routes_notes import notes_bp
from routes_today import today_bp
from routes_systems import systems_bp
from routes_files import files_bp
from routes_outreach_hub import outreach_hub_bp
from routes_content import content_bp
from routes_outcomes import outcomes_bp
from config import now_ph, today_ph

app.register_blueprint(spend_bp)
app.register_blueprint(command_bp)
app.register_blueprint(brief_bp)
app.register_blueprint(deal_bp)
app.register_blueprint(ops_bp)
app.register_blueprint(notes_bp)
app.register_blueprint(today_bp)
app.register_blueprint(systems_bp)
app.register_blueprint(files_bp)
app.register_blueprint(outreach_hub_bp)
app.register_blueprint(content_bp)
app.register_blueprint(outcomes_bp)


# ============================================================
# Auth middleware
# ============================================================

from config import get_dashboard_token

EXEMPT_PATHS = {'/login', '/api/auth/verify'}
EXEMPT_PREFIXES = ('/static/',)


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    token = request.json.get('token', '')
    expected = get_dashboard_token()
    if expected and token == expected:
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401


@app.before_request
def _check_auth():
    """Check bearer token on all requests (except login + static)."""
    # Skip auth if no token configured
    expected = get_dashboard_token()
    if not expected:
        return

    # Exempt paths
    if request.path in EXEMPT_PATHS:
        return
    for prefix in EXEMPT_PREFIXES:
        if request.path.startswith(prefix):
            return

    # Check Authorization header or cookie
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''

    # Also check X-Token header (easier for fetch calls from JS)
    if not token:
        token = request.headers.get('X-Token', '')

    if token != expected:
        # Only gate API calls — frontend JS handles page auth via localStorage
        if request.path.startswith('/api/'):
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 401


def _migrate_habits_if_needed(service, sheet_id):
    """Migrate checklist config to v2 (21 items, 4 categories) if needed."""
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="'Checklist Config'"
    ).execute()
    rows = result.get('values', [])
    if len(rows) < 2:
        return

    # Check if already migrated
    existing_cats = {row[0] for row in rows[1:] if len(row) >= 1}
    if 'Family & Home' in existing_cats:
        return

    print("Migrating checklist config to v2...")

    # Build set of existing active item names
    existing_items = {}
    for i, row in enumerate(rows[1:], start=2):
        if len(row) >= 2:
            existing_items[row[1]] = i  # item name -> row number

    # New config (without header)
    new_items = [
        ['Personal', 'Gratitude', 'check', '1', 'TRUE'],
        ['Personal', 'Stretch', 'check', '2', 'TRUE'],
        ['Personal', 'Learn AI Automation', 'check', '3', 'TRUE'],
        ['Personal', 'Read Pages', 'count', '4', 'TRUE'],
        ['Personal', 'Cardio', 'check', '5', 'TRUE'],
        ['Workout', 'Pullups', 'count', '1', 'TRUE'],
        ['Workout', 'Dips', 'count', '2', 'TRUE'],
        ['Workout', 'Shoulder Press', 'count', '3', 'TRUE'],
        ['Workout', 'Pushups', 'count', '4', 'TRUE'],
        ['Workout', 'Squats', 'count', '5', 'TRUE'],
        ['EPS', 'Practice Scripts', 'check', '1', 'TRUE'],
        ['EPS', 'Check Sent Quotes', 'check', '2', 'TRUE'],
        ['EPS', 'Check Follow Ups', 'check', '3', 'TRUE'],
        ['EPS', 'Sales Calls', 'count', '4', 'TRUE'],
        ['EPS', 'Discovery Calls', 'count', '5', 'TRUE'],
        ['EPS', 'Cold Calls', 'count', '6', 'TRUE'],
        ['Family & Home', 'Bathe & Brush Marcus', 'check', '1', 'TRUE'],
        ['Family & Home', 'Wife Time', 'check', '2', 'TRUE'],
        ['Family & Home', 'Clean Up Office', 'check', '3', 'TRUE'],
        ['Family & Home', 'Clean Up Living Room', 'check', '4', 'TRUE'],
        ['Family & Home', 'Clean Up Room', 'check', '5', 'TRUE'],
    ]
    new_item_names = {row[1] for row in new_items}

    # Mark old items not in new list as inactive
    updates = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) >= 2 and row[1] not in new_item_names:
            active_col = 4 if len(row) >= 5 else len(row) - 1
            updates.append({
                'range': f"'Checklist Config'!E{i}",
                'values': [['FALSE']],
            })

    # Update existing items that moved category/order
    for new_row in new_items:
        name = new_row[1]
        if name in existing_items:
            row_num = existing_items[name]
            updates.append({
                'range': f"'Checklist Config'!A{row_num}:E{row_num}",
                'values': [new_row],
            })

    # Append truly new items
    items_to_append = [row for row in new_items if row[1] not in existing_items]
    if items_to_append:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="'Checklist Config'!A:E",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': items_to_append},
        ).execute()

    # Batch update existing rows
    if updates:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={'valueInputOption': 'RAW', 'data': updates},
        ).execute()

    print("Checklist config migrated to v2.")


@app.before_request
def _ensure_init():
    """Lazy init: SQLite, Sheets sync, blueprints on first request."""
    if not hasattr(app, '_bp_initialized'):
        # Init SQLite
        db.init_db()

        sheet_id = get_sheet_id()
        service = _svc()
        try:
            _migrate_habits_if_needed(service, sheet_id)
        except Exception as e:
            print(f"[warn] habits migration skipped: {e}")

        # Pull from Sheets → SQLite on first boot (or if DB is empty)
        if db.is_empty():
            sync.sync_from_sheets(service, sheet_id)

        # Start background sync (SQLite → Sheets every 60s)
        sync.start_background_sync(service, sheet_id)

        init_spend(service, sheet_id)
        init_command(service, sheet_id)
        init_brief(service)
        app._bp_initialized = True


if __name__ == '__main__':
    import os
    # Pre-init sheet
    get_sheet_id()
    print("Enriquez OS Dashboard → http://localhost:5002")
    print(f"Mobile access   → http://192.168.100.179:5002")
    # Only warm cache in the reloader child process (not the parent watcher)
    # This prevents thread segfaults when the reloader kills the parent
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Pre-warming caches...")
        warm_cache()
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
