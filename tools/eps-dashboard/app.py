"""
EPS Sales & Operations Dashboard.

Live Pipedrive data + EOD intelligence overlay.
Usage: python3 tools/eps-dashboard/app.py
Opens at http://localhost:5050
"""

import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import pipedrive_client as pd_client
import data_loader
from config import get_dashboard_token, now_aest

CRM_CACHE_DB = Path(__file__).parent.parent.parent / '.tmp' / 'crm_cache.db'

app = Flask(__name__)

# --- Cache ---
_cache = {'deals': [], 'projects': [], 'last_fetch': None}
CACHE_TTL = 300  # 5 minutes


def _is_cache_fresh():
    if not _cache['last_fetch']:
        return False
    elapsed = (now_aest() - _cache['last_fetch']).total_seconds()
    return elapsed < CACHE_TTL


def _refresh_cache():
    """Pull fresh data from Pipedrive and merge with EOD."""
    deals = pd_client.fetch_all_deals()
    deals = data_loader.merge_deals_with_eod(deals)
    projects = pd_client.fetch_all_projects()
    projects = data_loader.merge_projects_with_eod(projects)
    _cache['deals'] = deals
    _cache['projects'] = projects
    _cache['last_fetch'] = now_aest()
    return deals, projects


def _get_data(force=False):
    """Get deals and projects, from cache if fresh."""
    if force or not _is_cache_fresh():
        return _refresh_cache()
    return _cache['deals'], _cache['projects']


# --- Auth ---

EXEMPT_PATHS = {'/login', '/api/auth/verify'}
EXEMPT_PREFIXES = ('/static/',)


@app.before_request
def _check_auth():
    expected = get_dashboard_token()
    if not expected:
        return
    if request.path in EXEMPT_PATHS:
        return
    for prefix in EXEMPT_PREFIXES:
        if request.path.startswith(prefix):
            return
    token = request.headers.get('X-Token', '')
    if not token:
        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
    if token != expected and request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401


@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    token = request.json.get('token', '')
    expected = get_dashboard_token()
    if expected and token == expected:
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401


# --- Page routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('index.html')


# --- API routes ---

@app.route('/api/overview')
def api_overview():
    deals, projects = _get_data()
    tenders = data_loader.load_tenders()
    questions = data_loader.load_questions()
    stats = data_loader.get_overview_stats(deals, projects, tenders, questions)
    crm_sync = data_loader.load_crm_sync()

    # Attention items: flagged deals + flagged projects
    attention = []
    for d in deals:
        if d.get('flags'):
            attention.append({
                'type': 'deal',
                'id': d['deal_id'],
                'title': d['title'],
                'stage': d['stage'],
                'pipeline': d['pipeline'],
                'value': d['value'],
                'flags': d['flags'],
                'next_action': d['next_action'],
                'days_since_activity': d['days_since_activity'],
                'client': d['client'],
            })
    for p in projects:
        if p.get('flags'):
            attention.append({
                'type': 'project',
                'id': p['project_id'],
                'title': p['title'],
                'phase': p['phase'],
                'board': p['board'],
                'flags': p['flags'],
                'next_action': p['next_action'],
                'days_since_update': p['days_since_update'],
            })
    attention.sort(key=lambda x: len(x.get('flags', [])), reverse=True)

    last_sync = crm_sync.get('timestamp', '') if isinstance(crm_sync, dict) else ''

    return jsonify({
        'ok': True,
        'stats': stats,
        'attention': attention,
        'questions': questions,
        'last_fetch': _cache['last_fetch'].strftime('%Y-%m-%d %H:%M') if _cache['last_fetch'] else '',
        'last_sync': last_sync,
    })


@app.route('/api/deals')
def api_deals():
    deals, _ = _get_data()
    pipeline = request.args.get('pipeline', '')
    stage = request.args.get('stage', '')
    sort_by = request.args.get('sort', 'days_since_activity')
    sort_dir = request.args.get('dir', 'desc')

    filtered = list(deals)
    if pipeline:
        filtered = [d for d in filtered if d['pipeline'] == pipeline]
    if stage:
        filtered = [d for d in filtered if d['stage'] == stage]

    reverse = sort_dir == 'desc'
    if sort_by == 'value':
        filtered.sort(key=lambda d: d.get('value', 0), reverse=reverse)
    elif sort_by == 'last_activity':
        filtered.sort(key=lambda d: d.get('last_activity', ''), reverse=reverse)
    elif sort_by == 'title':
        filtered.sort(key=lambda d: d.get('title', '').lower(), reverse=not reverse)
    else:
        filtered.sort(key=lambda d: d.get('days_since_activity', 0), reverse=reverse)

    # Stage counts for pipeline bar
    stage_counts = {}
    for d in deals:
        s = d['stage']
        stage_counts[s] = stage_counts.get(s, 0) + 1

    return jsonify({
        'ok': True,
        'deals': filtered,
        'total': len(filtered),
        'stage_counts': stage_counts,
        'last_fetch': _cache['last_fetch'].strftime('%Y-%m-%d %H:%M') if _cache['last_fetch'] else '',
    })


@app.route('/api/tenders')
def api_tenders():
    tenders = data_loader.load_tenders()
    return jsonify({
        'ok': True,
        'leads': tenders['leads'],
        'open_tenders': tenders['open_tenders'],
        'scraped_at': tenders['scraped_at'],
        'leads_count': len(tenders['leads']),
        'open_count': len(tenders['open_tenders']),
    })


@app.route('/api/projects')
def api_projects():
    _, projects = _get_data()
    board = request.args.get('board', '')
    phase = request.args.get('phase', '')

    filtered = list(projects)
    if board:
        filtered = [p for p in filtered if p['board'] == board]
    if phase:
        filtered = [p for p in filtered if p['phase'] == phase]

    filtered.sort(key=lambda p: p.get('days_since_update', 0), reverse=True)

    # Phase counts
    phase_counts = {}
    for p in projects:
        ph = p['phase']
        phase_counts[ph] = phase_counts.get(ph, 0) + 1

    return jsonify({
        'ok': True,
        'projects': filtered,
        'total': len(filtered),
        'phase_counts': phase_counts,
        'last_fetch': _cache['last_fetch'].strftime('%Y-%m-%d %H:%M') if _cache['last_fetch'] else '',
    })


@app.route('/api/deal/<int:deal_id>')
def api_deal_detail(deal_id):
    """Deal detail — live Pipedrive data + SM8 status + sync history from cache."""
    deals, projects = _get_data()
    deal = next((d for d in deals if d['deal_id'] == deal_id), None)
    if not deal:
        return jsonify({'ok': False, 'error': 'Deal not found'}), 404

    # SM8 cache + sync history + activities from SQLite
    sm8_info = {}
    sync_history = []
    sm8_activities = []
    sm8_files = []
    if CRM_CACHE_DB.exists():
        try:
            conn = sqlite3.connect(str(CRM_CACHE_DB))
            row = conn.execute(
                "SELECT sm8_number, sm8_status, address, last_synced FROM deals WHERE deal_id = ?",
                (deal_id,)
            ).fetchone()
            if row:
                sm8_info = {
                    'sm8_number': row[0] or '',
                    'sm8_status': row[1] or '',
                    'address': row[2] or '',
                    'last_synced': row[3] or '',
                }
            # Sync log — status changes for this deal
            logs = conn.execute(
                "SELECT field, old_value, new_value, source, timestamp "
                "FROM sync_log WHERE deal_id = ? ORDER BY id DESC LIMIT 20",
                (deal_id,)
            ).fetchall()
            sync_history = [
                {'field': l[0], 'old': l[1], 'new': l[2], 'source': l[3], 'time': l[4]}
                for l in logs
            ]
            # SM8 activities
            act_rows = conn.execute(
                "SELECT note, start_date, end_date, was_scheduled, staff_name, activity_uuid "
                "FROM sm8_activities WHERE deal_id = ? ORDER BY start_date DESC LIMIT 20",
                (deal_id,)
            ).fetchall()
            sm8_activities = [
                {'note': r[0] or '', 'start_date': r[1] or '', 'end_date': r[2] or '',
                 'is_site_visit': bool(r[3]), 'staff': r[4] or '', 'uuid': r[5]}
                for r in act_rows
            ]
            # SM8 files
            file_rows = conn.execute(
                "SELECT file_uuid, file_name, file_type "
                "FROM sm8_files WHERE deal_id = ? ORDER BY created_at DESC LIMIT 30",
                (deal_id,)
            ).fetchall()
            sm8_files = [
                {'uuid': r[0], 'name': r[1] or '', 'type': r[2] or ''}
                for r in file_rows
            ]
            conn.close()
        except Exception:
            pass

    # Linked projects
    linked_projects = [p for p in projects if deal_id in (p.get('deal_ids') or [])]

    # EOD context
    eod = data_loader.load_eod_deal(deal_id)

    # Pipedrive notes
    try:
        notes = pd_client.fetch_deal_notes(deal_id)
    except Exception:
        notes = []

    return jsonify({
        'ok': True,
        'deal': deal,
        'sm8': sm8_info,
        'sm8_activities': sm8_activities,
        'sm8_files': sm8_files,
        'sync_history': sync_history,
        'linked_projects': linked_projects,
        'notes': notes,
        'eod': {
            'flags': eod.get('flags', []),
            'next_action': eod.get('next_action', ''),
            'questions': eod.get('questions', []),
        },
    })


@app.route('/api/project/<int:project_id>')
def api_project_detail(project_id):
    """Project detail — project data + SM8 activities from linked deal."""
    _, projects = _get_data()
    proj = next((p for p in projects if p['project_id'] == project_id), None)
    if not proj:
        return jsonify({'ok': False, 'error': 'Project not found'}), 404

    sm8_info = {}
    sm8_activities = []
    sm8_files = []
    linked_deal_id = (proj.get('deal_ids') or [None])[0]

    if linked_deal_id and CRM_CACHE_DB.exists():
        try:
            conn = sqlite3.connect(str(CRM_CACHE_DB))
            row = conn.execute(
                "SELECT sm8_number, sm8_status, address, last_synced FROM deals WHERE deal_id = ?",
                (linked_deal_id,)
            ).fetchone()
            if row:
                sm8_info = {
                    'sm8_number': row[0] or '', 'sm8_status': row[1] or '',
                    'address': row[2] or '', 'last_synced': row[3] or '',
                }
            act_rows = conn.execute(
                "SELECT note, start_date, end_date, was_scheduled, staff_name, activity_uuid "
                "FROM sm8_activities WHERE deal_id = ? ORDER BY start_date DESC LIMIT 20",
                (linked_deal_id,)
            ).fetchall()
            sm8_activities = [
                {'note': r[0] or '', 'start_date': r[1] or '', 'end_date': r[2] or '',
                 'is_site_visit': bool(r[3]), 'staff': r[4] or '', 'uuid': r[5]}
                for r in act_rows
            ]
            file_rows = conn.execute(
                "SELECT file_uuid, file_name, file_type "
                "FROM sm8_files WHERE deal_id = ? ORDER BY created_at DESC LIMIT 30",
                (linked_deal_id,)
            ).fetchall()
            sm8_files = [
                {'uuid': r[0], 'name': r[1] or '', 'type': r[2] or ''}
                for r in file_rows
            ]
            conn.close()
        except Exception:
            pass

    eod = data_loader.load_eod_project(project_id)

    return jsonify({
        'ok': True,
        'project': proj,
        'sm8': sm8_info,
        'sm8_activities': sm8_activities,
        'sm8_files': sm8_files,
        'linked_deal_id': linked_deal_id,
        'eod': {
            'flags': eod.get('flags', []),
            'next_action': eod.get('next_action', ''),
        },
    })


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Force refresh from Pipedrive."""
    deals, projects = _get_data(force=True)
    return jsonify({
        'ok': True,
        'deals_count': len(deals),
        'projects_count': len(projects),
        'last_fetch': _cache['last_fetch'].strftime('%Y-%m-%d %H:%M') if _cache['last_fetch'] else '',
    })


@app.route('/api/refresh-analysis', methods=['POST'])
def api_refresh_analysis():
    """Run EOD ops manager on demand, then refresh cache."""
    base_dir = Path(__file__).parent.parent.parent
    tool_path = base_dir / 'tools' / 'eod_ops_manager.py'

    def run_analysis():
        subprocess.run(
            [sys.executable, str(tool_path)],
            cwd=str(base_dir),
            capture_output=True,
            timeout=120,
        )

    t = threading.Thread(target=run_analysis)
    t.start()

    return jsonify({
        'ok': True,
        'message': 'Analysis started. Refresh in ~60 seconds to see updated flags.',
    })


# --- Main ---

if __name__ == '__main__':
    print("EPS Dashboard: http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=True)
