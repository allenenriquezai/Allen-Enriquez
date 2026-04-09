"""
Spend Tracker routes — bolted onto the main dashboard app.

Usage in app.py:
    from routes_spend import spend_bp
    app.register_blueprint(spend_bp)
"""

from datetime import datetime, timedelta
from config import now_ph, today_ph

from flask import Blueprint, jsonify, request

import db

spend_bp = Blueprint('spend', __name__)

# These get set by app.py after Sheet init (kept for backward compat)
_sheets_service = None
_sheet_id = None


def init_spend(sheets_service, sheet_id):
    global _sheets_service, _sheet_id
    _sheets_service = sheets_service
    _sheet_id = sheet_id


@spend_bp.route('/api/spend/<date>')
def get_spend(date):
    """Get spend entries for a specific date (YYYY-MM-DD)."""
    try:
        entries = db.load_spend(date)
        for i, e in enumerate(entries):
            e['index'] = i
            e['amount'] = str(e['amount'])

        takeout = sum(float(e['amount'] or 0) for e in entries if e.get('category', '').lower() == 'takeout')
        general = sum(float(e['amount'] or 0) for e in entries if e.get('category', '').lower() == 'general')
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
        db.save_spend(date, category, amount, description)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/<date>/<int:index>', methods=['DELETE'])
def delete_spend(date, index):
    """Delete a spend entry by index within a date."""
    try:
        entries = db.load_spend(date)
        if index >= len(entries):
            return jsonify({'ok': False, 'error': 'Entry not found'}), 404

        db.delete_spend(entries[index]['id'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/summary')
def spend_summary():
    """Weekly spend summary with comparison."""
    try:
        today = now_ph().date()

        # This week (Mon-Sun)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Last week
        last_start = week_start - timedelta(days=7)
        last_end = week_start - timedelta(days=1)

        # Load from SQLite
        this_week_rows = db.load_spend_range(
            week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d'))
        last_week_rows = db.load_spend_range(
            last_start.strftime('%Y-%m-%d'), last_end.strftime('%Y-%m-%d'))

        def summarize(rows):
            takeout = sum(r['amount'] for r in rows if r['category'].lower() == 'takeout')
            general = sum(r['amount'] for r in rows if r['category'].lower() == 'general')
            total = takeout + general
            days = len(set(r['date'] for r in rows)) or 1
            return {
                'takeout': takeout,
                'general': general,
                'total': total,
                'daily_avg': round(total / days, 2),
                'count': len(rows),
            }

        return jsonify({
            'ok': True,
            'this_week': summarize(this_week_rows),
            'last_week': summarize(last_week_rows),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
