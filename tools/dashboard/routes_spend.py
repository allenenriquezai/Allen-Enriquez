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

        # This week (Sun-Sat)
        week_start = today - timedelta(days=(today.weekday() + 1) % 7)
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


@spend_bp.route('/api/spend/weekly')
def spend_weekly():
    """Per-day spend breakdown for the current week (Sun–Sat)."""
    try:
        today = now_ph().date()
        week_start = today - timedelta(days=(today.weekday() + 1) % 7)
        week_end = week_start + timedelta(days=6)

        rows = db.load_spend_range(
            week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d'))

        # Group by date
        by_date = {}
        for r in rows:
            d = r['date']
            if d not in by_date:
                by_date[d] = {'takeout': 0.0, 'general': 0.0}
            cat = r['category'].lower()
            if cat == 'takeout':
                by_date[d]['takeout'] += r['amount']
            else:
                by_date[d]['general'] += r['amount']

        days = []
        d = week_start
        while d <= week_end:
            key = d.strftime('%Y-%m-%d')
            entry = by_date.get(key, {'takeout': 0.0, 'general': 0.0})
            days.append({
                'date': key,
                'day': d.strftime('%a'),
                'is_today': key == today.strftime('%Y-%m-%d'),
                'takeout': entry['takeout'],
                'general': entry['general'],
                'total': entry['takeout'] + entry['general'],
            })
            d += timedelta(days=1)

        week_total = sum(day['total'] for day in days)
        return jsonify({
            'ok': True,
            'days': days,
            'week_total': week_total,
            'week_takeout': sum(day['takeout'] for day in days),
            'week_general': sum(day['general'] for day in days),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@spend_bp.route('/api/spend/monthly')
def spend_monthly():
    """Per-day spend for the current calendar month + totals."""
    try:
        today = now_ph().date()
        month_start = today.replace(day=1)
        # Last day of month
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        rows = db.load_spend_range(
            month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))

        by_date = {}
        for r in rows:
            d = r['date']
            if d not in by_date:
                by_date[d] = {'takeout': 0.0, 'general': 0.0}
            cat = r['category'].lower()
            if cat == 'takeout':
                by_date[d]['takeout'] += r['amount']
            else:
                by_date[d]['general'] += r['amount']

        days = []
        d = month_start
        while d <= month_end:
            key = d.strftime('%Y-%m-%d')
            entry = by_date.get(key, {'takeout': 0.0, 'general': 0.0})
            days.append({
                'date': key,
                'day_num': d.day,
                'is_today': key == today.strftime('%Y-%m-%d'),
                'takeout': entry['takeout'],
                'general': entry['general'],
                'total': entry['takeout'] + entry['general'],
            })
            d += timedelta(days=1)

        month_total = sum(day['total'] for day in days)
        days_with_spend = sum(1 for day in days if day['total'] > 0)
        return jsonify({
            'ok': True,
            'month': today.strftime('%B %Y'),
            'days': days,
            'month_total': month_total,
            'month_takeout': sum(day['takeout'] for day in days),
            'month_general': sum(day['general'] for day in days),
            'daily_avg': round(month_total / days_with_spend, 2) if days_with_spend else 0,
            'days_with_spend': days_with_spend,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
