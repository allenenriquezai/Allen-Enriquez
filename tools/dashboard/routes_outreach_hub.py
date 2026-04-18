"""
Outreach Hub v1 — prospect list + pipeline view for Brand > Outreach.

Replaces the thin counter-only sub-pill with a real prospect browser.
Source of truth: PH Prospects Google Sheet (via tools/outreach.py helpers).

Endpoints:
    GET /api/brand/outreach/prospects?channel=all&stage=all&limit=100
    GET /api/brand/outreach/pipeline
    GET /api/brand/outreach/templates
    GET /api/brand/outreach/sources

Cache: disk-backed at .tmp/outreach_prospects_cache.json (60s TTL).
Gunicorn has multiple workers — NEVER use in-memory cache. Disk only.

Registration in app.py:
    from routes_outreach_hub import outreach_hub_bp
    app.register_blueprint(outreach_hub_bp)
"""

import json
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import now_ph, today_ph

outreach_hub_bp = Blueprint('outreach_hub', __name__)

# Add tools/ to path so we can import outreach modules
sys.path.insert(0, str(Path(__file__).parent.parent))

PH_TZ = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
REPO_TMP = BASE_DIR / '.tmp'
PERSONAL_DIR = BASE_DIR / 'projects' / 'personal'
PERSONAL_TMP = PERSONAL_DIR / '.tmp'

# Templates live at projects/personal/templates/outreach/*.md (actual layout).
# Spec mentions projects/personal/outreach/templates/ — try both.
TEMPLATE_DIRS = [
    PERSONAL_DIR / 'templates' / 'outreach',
    PERSONAL_DIR / 'outreach' / 'templates',
]

FB_GROUPS_CACHE = PERSONAL_TMP / 'fb_groups_list.json'

PROSPECTS_CACHE_FILE = REPO_TMP / 'outreach_prospects_cache.json'
CACHE_TTL = 60.0  # seconds


# ============================================================
# Stage mapping
# ============================================================

STAGE_ORDER = ['discover', 'enrich', 'messaged', 'replied', 'booked', 'cold']
STAGE_LABELS = {
    'discover': 'Discover',
    'enrich': 'Enrich',
    'messaged': 'Messaged',
    'replied': 'Replied',
    'booked': 'Booked',
    'cold': 'Cold',
}


def _map_stage(status: str) -> str:
    s = (status or '').strip().lower()
    if not s:
        return 'discover'
    if s == 'enriched':
        return 'enrich'
    if s in ('t1_sent', 't2_sent', 't3_sent'):
        return 'messaged'
    if s.startswith('replied'):
        return 'replied'
    if s == 'booked':
        return 'booked'
    if s == 'cold':
        return 'cold'
    return 'discover'


def _derive_channel(fb_url: str) -> str:
    u = (fb_url or '').lower()
    if not u:
        return 'fb_dm'
    if '/groups/' in u:
        return 'fb_group'
    return 'fb_dm'


def _parse_date_safe(s: str):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _last_touch(row: dict):
    """Return (date_str, template, touch_num) for the latest non-empty Touch N Date."""
    last_num = 0
    last_date = ''
    last_tpl = ''
    for n in (1, 2, 3):
        d = (row.get(f'Touch {n} Date') or '').strip()
        t = (row.get(f'Touch {n} Template') or '').strip()
        if d:
            last_num = n
            last_date = d
            last_tpl = t
    return last_date, last_tpl, last_num


def _next_action(row: dict, stage: str, today: date) -> str:
    """Suggest a next move per row."""
    status = (row.get('Status') or '').strip().lower()
    reply = (row.get('Reply') or '').strip()

    if stage == 'discover':
        return 'Enrich profile'
    if stage == 'enrich':
        return 'Send T1'
    if stage == 'messaged':
        # Find which touch was last and when next should fire (rough 3/5 day rule)
        _, _, last_num = _last_touch(row)
        wait = {1: 3, 2: 5, 3: 7}.get(last_num, 3)
        last_d = _parse_date_safe(row.get(f'Touch {last_num} Date', '')) if last_num else None
        if last_d:
            due = last_d + timedelta(days=wait)
            if today >= due and last_num < 3:
                return f'Send T{last_num + 1}'
            if last_num >= 3 and today >= due:
                return 'Mark cold'
            return f'Follow-up T{last_num + 1} due {due.isoformat()}'
        return f'Send T{last_num + 1}' if last_num < 3 else 'Mark cold'
    if stage == 'replied':
        if status == 'replied_warm':
            return 'Book call'
        if status == 'replied_question':
            return 'Draft reply'
        return 'Review reply'
    if stage == 'booked':
        return 'Prep for call'
    if stage == 'cold':
        return 'Archive'
    return '—'


# ============================================================
# Sheet fetch
# ============================================================

def _fetch_prospects_from_sheet():
    """Hit the PH Prospects sheet. Return list of mapped dicts."""
    try:
        from outreach import load_config, sheets_service, load_env
        from outreach_lifecycle import _read_prospects
    except Exception:
        traceback.print_exc()
        return None, 'failed to import outreach helpers'

    try:
        load_env()
        cfg = load_config()
        sid = cfg['spreadsheet_id']
        svc = sheets_service()
        _headers, rows = _read_prospects(svc, sid)
    except Exception as e:
        traceback.print_exc()
        return None, str(e)

    today = now_ph().date()
    out = []
    for r in rows:
        row_id = r.get('_row')
        name = (r.get('Name') or '').strip()
        fb_url = (r.get('FB URL') or '').strip()
        status = (r.get('Status') or '').strip()
        segment = (r.get('Segment') or '').strip()
        reply = (r.get('Reply') or '').strip()
        notes = (r.get('Notes') or '').strip()

        stage = _map_stage(status)
        channel = _derive_channel(fb_url)
        last_date, last_tpl, _ = _last_touch(r)
        next_action = _next_action(r, stage, today)

        out.append({
            'id': row_id,
            'name': name or f'Row {row_id}',
            'fb_url': fb_url,
            'channel': channel,
            'stage': stage,
            'status': status,
            'segment': segment,
            'last_touch_date': last_date,
            'last_touch_template': last_tpl,
            'next_action': next_action,
            'reply_snippet': reply[:140],
            'notes': notes[:280],
            'touches': {
                't1_date': (r.get('Touch 1 Date') or '').strip(),
                't1_template': (r.get('Touch 1 Template') or '').strip(),
                't2_date': (r.get('Touch 2 Date') or '').strip(),
                't2_template': (r.get('Touch 2 Template') or '').strip(),
                't3_date': (r.get('Touch 3 Date') or '').strip(),
                't3_template': (r.get('Touch 3 Template') or '').strip(),
            },
        })
    return out, None


# ============================================================
# Disk cache
# ============================================================

def _cache_read():
    try:
        if not PROSPECTS_CACHE_FILE.exists():
            return None
        age = time.time() - PROSPECTS_CACHE_FILE.stat().st_mtime
        if age >= CACHE_TTL:
            return None
        return json.loads(PROSPECTS_CACHE_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_write(payload):
    try:
        PROSPECTS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROSPECTS_CACHE_FILE.write_text(json.dumps(payload), encoding='utf-8')
    except OSError:
        pass


def _get_all_prospects():
    """Return cached prospect list, refreshing from sheet if stale. Payload includes
    the raw prospect list + computed counts + last_refreshed iso."""
    cached = _cache_read()
    if cached is not None:
        return cached

    prospects, err = _fetch_prospects_from_sheet()
    if prospects is None:
        # Serve stale if available
        try:
            if PROSPECTS_CACHE_FILE.exists():
                stale = json.loads(PROSPECTS_CACHE_FILE.read_text(encoding='utf-8'))
                stale['error'] = err
                stale['stale'] = True
                return stale
        except (OSError, json.JSONDecodeError):
            pass
        return {
            'prospects': [],
            'counts': {'by_stage': {}, 'by_channel': {}},
            'last_refreshed': now_ph().isoformat(),
            'error': err,
        }

    by_stage = {s: 0 for s in STAGE_ORDER}
    by_channel = {'fb_group': 0, 'fb_dm': 0}
    for p in prospects:
        by_stage[p['stage']] = by_stage.get(p['stage'], 0) + 1
        by_channel[p['channel']] = by_channel.get(p['channel'], 0) + 1

    payload = {
        'prospects': prospects,
        'counts': {'by_stage': by_stage, 'by_channel': by_channel},
        'last_refreshed': now_ph().isoformat(),
        'error': None,
    }
    _cache_write(payload)
    return payload


# ============================================================
# Routes
# ============================================================

@outreach_hub_bp.route('/api/brand/outreach/prospects')
def api_prospects():
    try:
        channel = (request.args.get('channel') or 'all').strip().lower()
        stage = (request.args.get('stage') or 'all').strip().lower()
        try:
            limit = int(request.args.get('limit') or 100)
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 1000))

        data = _get_all_prospects()
        prospects = data.get('prospects') or []

        if channel != 'all':
            prospects = [p for p in prospects if p['channel'] == channel]
        if stage != 'all':
            prospects = [p for p in prospects if p['stage'] == stage]

        # Priority sort: replied > messaged (overdue) > enrich > discover > booked > cold
        priority = {'replied': 0, 'messaged': 1, 'enrich': 2, 'discover': 3, 'booked': 4, 'cold': 5}
        prospects.sort(key=lambda p: (priority.get(p['stage'], 9), p.get('name', '')))

        prospects = prospects[:limit]

        return jsonify({
            'ok': True,
            'prospects': prospects,
            'counts': data.get('counts') or {'by_stage': {}, 'by_channel': {}},
            'last_refreshed': data.get('last_refreshed'),
            'error': data.get('error'),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@outreach_hub_bp.route('/api/brand/outreach/pipeline')
def api_pipeline():
    try:
        data = _get_all_prospects()
        prospects = data.get('prospects') or []

        # Group by stage, take top 5 per stage
        by_stage = {s: [] for s in STAGE_ORDER}
        for p in prospects:
            by_stage.setdefault(p['stage'], []).append(p)

        lanes = []
        for stage in STAGE_ORDER:
            stage_prospects = by_stage.get(stage, [])
            # Sort by last_touch_date desc (most recent first), fall back to name
            stage_prospects.sort(
                key=lambda p: (p.get('last_touch_date') or '', p.get('name') or ''),
                reverse=True,
            )
            top = [
                {
                    'id': p['id'],
                    'name': p['name'],
                    'last_touch_date': p['last_touch_date'],
                    'channel': p['channel'],
                    'next_action': p['next_action'],
                }
                for p in stage_prospects[:5]
            ]
            lanes.append({
                'stage': stage,
                'label': STAGE_LABELS[stage],
                'count': len(stage_prospects),
                'prospects': top,
            })

        return jsonify({
            'ok': True,
            'lanes': lanes,
            'last_refreshed': data.get('last_refreshed'),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Templates
# ============================================================

def _infer_channel_from_filename(name: str) -> str:
    n = name.lower()
    if n.startswith('fb_group') or '_fb_group' in n:
        return 'fb_group'
    if n.startswith('fb_dm') or '_fb_dm' in n:
        return 'fb_dm'
    if n.startswith('email') or '_email' in n:
        return 'email'
    if '_fb_' in n or n.endswith('_fb.md'):
        # Ambiguous FB — default to dm
        return 'fb_dm'
    return 'misc'


@outreach_hub_bp.route('/api/brand/outreach/templates')
def api_templates():
    try:
        # Gather template files from all candidate dirs
        files = []
        for d in TEMPLATE_DIRS:
            if d.exists():
                files.extend(sorted(d.glob('*.md')))
        if not files:
            return jsonify({'ok': True, 'templates': []})

        # Join with prospect usage for last_used + use_count
        data = _get_all_prospects()
        prospects = data.get('prospects') or []
        usage = {}  # template_name -> {'count': int, 'last_used': 'YYYY-MM-DD'}
        for p in prospects:
            touches = p.get('touches') or {}
            for n in (1, 2, 3):
                tpl = (touches.get(f't{n}_template') or '').strip()
                d_str = (touches.get(f't{n}_date') or '').strip()
                if not tpl:
                    continue
                entry = usage.setdefault(tpl, {'count': 0, 'last_used': ''})
                entry['count'] += 1
                if d_str and d_str > (entry['last_used'] or ''):
                    entry['last_used'] = d_str

        templates = []
        for f in files:
            try:
                raw = f.read_text(encoding='utf-8')
            except OSError:
                raw = ''
            preview = raw.strip()[:180]
            name = f.stem
            ch = _infer_channel_from_filename(f.name)
            u = usage.get(name, {'count': 0, 'last_used': ''})
            templates.append({
                'name': name,
                'channel': ch,
                'preview': preview,
                'last_used': u['last_used'],
                'use_count': u['count'],
            })

        # Sort by use_count desc
        templates.sort(key=lambda t: (-t['use_count'], t['name']))

        return jsonify({'ok': True, 'templates': templates})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Sources (FB groups)
# ============================================================

@outreach_hub_bp.route('/api/brand/outreach/sources')
def api_sources():
    try:
        if FB_GROUPS_CACHE.exists():
            try:
                data = json.loads(FB_GROUPS_CACHE.read_text(encoding='utf-8'))
                sources = data if isinstance(data, list) else data.get('sources', [])
                return jsonify({'ok': True, 'sources': sources})
            except (OSError, json.JSONDecodeError):
                pass
        return jsonify({
            'ok': True,
            'sources': [],
            'note': 'FB groups sheet not yet cached locally',
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500
