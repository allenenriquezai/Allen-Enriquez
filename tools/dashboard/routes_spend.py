"""
Spend Tracker routes — bolted onto the main dashboard app.

Usage in app.py:
    from routes_spend import spend_bp
    app.register_blueprint(spend_bp)
"""

from datetime import datetime
from config import now_ph, today_ph

from flask import Blueprint, jsonify, request

spend_bp = Blueprint('spend', __name__)

# These get set by app.py after Sheet init
_sheets_service = None
_sheet_id = None
SPEND_TAB = 'Spend Log'


def init_spend(sheets_service, sheet_id):
    global _sheets_service, _sheet_id
    _sheets_service = sheets_service
    _sheet_id = sheet_id


def _svc():
    """Lazy service getter (refreshes if token expired)."""
    global _sheets_service
    if _sheets_service is None:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from personal_crm import get_sheets_service
        _sheets_service = get_sheets_service()
    return _sheets_service


def _read_spend_tab():
    """Read all rows from Spend Log tab."""
    result = _svc().spreadsheets().values().get(
        spreadsheetId=_sheet_id,
        range=f"'{SPEND_TAB}'"
    ).execute()
    rows = result.get('values', [])
    if not rows:
        return [], {}
    headers = rows[0]
    col_map = {h: i for i, h in enumerate(headers)}
    return rows[1:], col_map


@spend_bp.route('/api/spend/<date>')
def get_spend(date):
    """Get spend entries for a specific date (YYYY-MM-DD)."""
    try:
        rows, col_map = _read_spend_tab()
        entries = []
        for i, row in enumerate(rows):
            row_date = row[col_map.get('Date', 0)] if col_map.get('Date', 0) < len(row) else ''
            if row_date == date:
                entries.append({
                    'index': i,
                    'date': row_date,
                    'category': row[col_map['Category']] if col_map.get('Category', 99) < len(row) else '',
                    'amount': row[col_map['Amount']] if col_map.get('Amount', 99) < len(row) else '0',
                    'description': row[col_map['Description']] if col_map.get('Description', 99) < len(row) else '',
                })
        # Calculate totals
        takeout = sum(float(e['amount'] or 0) for e in entries if e['category'].lower() == 'takeout')
        general = sum(float(e['amount'] or 0) for e in entries if e['category'].lower() == 'general')
        return jsonify({
            'ok': True,
            'entries': entries,
            'totals': {'takeout': takeout, 'general': general, 'total': takeout + general},
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/add', methods=['POST'])
def add_spend():
    """Add a spend entry."""
    data = request.json
    date = data.get('date')
    category = data.get('category', 'General')
    amount = data.get('amount')
    description = data.get('description', '')

    if not date or not amount:
        return jsonify({'ok': False, 'error': 'Missing date or amount'}), 400

    try:
        timestamp = now_ph().strftime('%Y-%m-%d %H:%M:%S')
        _svc().spreadsheets().values().append(
            spreadsheetId=_sheet_id,
            range=f"'{SPEND_TAB}'!A:E",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [[date, category, str(amount), description, timestamp]]},
        ).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/<date>/<int:index>', methods=['DELETE'])
def delete_spend(date, index):
    """Delete a spend entry by clearing its row (keeps sheet structure intact)."""
    try:
        rows, col_map = _read_spend_tab()
        # Find the actual row number (1-indexed, +1 for header)
        date_col = col_map.get('Date', 0)
        count = 0
        target_row = None
        for i, row in enumerate(rows):
            row_date = row[date_col] if date_col < len(row) else ''
            if row_date == date:
                if count == index:
                    target_row = i + 2  # +1 for header, +1 for 1-indexed
                    break
                count += 1

        if target_row is None:
            return jsonify({'ok': False, 'error': 'Entry not found'}), 404

        # Clear the row
        num_cols = len(col_map)
        end_col = chr(64 + num_cols) if num_cols <= 26 else 'E'
        _svc().spreadsheets().values().update(
            spreadsheetId=_sheet_id,
            range=f"'{SPEND_TAB}'!A{target_row}:{end_col}{target_row}",
            valueInputOption='RAW',
            body={'values': [[''] * num_cols]},
        ).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/summary')
def spend_summary():
    """Weekly spend summary with comparison."""
    try:
        from datetime import timedelta
        period = request.args.get('period', 'week')
        today = now_ph().date()

        rows, col_map = _read_spend_tab()
        date_col = col_map.get('Date', 0)
        cat_col = col_map.get('Category', 1)
        amt_col = col_map.get('Amount', 2)

        # Parse all entries
        all_entries = []
        for row in rows:
            if date_col >= len(row) or not row[date_col]:
                continue
            try:
                d = datetime.strptime(row[date_col], '%Y-%m-%d').date()
                cat = row[cat_col] if cat_col < len(row) else 'General'
                amt = float(row[amt_col]) if amt_col < len(row) and row[amt_col] else 0
                all_entries.append({'date': d, 'category': cat, 'amount': amt})
            except (ValueError, IndexError):
                continue

        # This week (Mon-Sun)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        this_week = [e for e in all_entries if week_start <= e['date'] <= week_end]

        # Last week
        last_start = week_start - timedelta(days=7)
        last_end = week_start - timedelta(days=1)
        last_week = [e for e in all_entries if last_start <= e['date'] <= last_end]

        def summarize(entries):
            takeout = sum(e['amount'] for e in entries if e['category'].lower() == 'takeout')
            general = sum(e['amount'] for e in entries if e['category'].lower() == 'general')
            total = takeout + general
            days = len(set(e['date'] for e in entries)) or 1
            return {
                'takeout': takeout,
                'general': general,
                'total': total,
                'daily_avg': round(total / days, 2),
                'count': len(entries),
            }

        return jsonify({
            'ok': True,
            'this_week': summarize(this_week),
            'last_week': summarize(last_week),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
