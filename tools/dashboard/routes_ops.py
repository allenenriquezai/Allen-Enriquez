"""
Ops routes — read-only operational status for PH outreach, US cold calls, and content.

Surfaces queue/lead/buffer state for Allen's 3 active systems on the dashboard.

Registration (do this in app.py manually after review):
    from routes_ops import ops_bp
    app.register_blueprint(ops_bp)

Endpoints:
    GET /api/ops/ph-outreach
    GET /api/ops/cold-calls
    GET /api/ops/content
    GET /api/ops/all
"""

import json
import re
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify

from config import now_ph

ops_bp = Blueprint('ops', __name__)

# Add tools/ to path so we can import outreach modules + lifecycle helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

PH_TZ = timezone(timedelta(hours=8))

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
TMP_DIR = BASE_DIR / 'projects' / 'personal' / '.tmp'
COLD_CALL_FILE = TMP_DIR / 'cold_call_leads.json'
CONTENT_BUFFER_FILE = TMP_DIR / 'content-buffer.json'
CONTENT_TRACKER_FILE = TMP_DIR / 'content_tracker.json'

# Cold call sequence schedule (matches tools/cold_call_followup.py)
COLD_CALL_SCHEDULE = [0, 2, 5, 10]


# ============================================================
# JSON file cache (mtime + 5s TTL)
# ============================================================

_FILE_CACHE: dict[str, dict] = {}
FILE_CACHE_TTL = 5.0  # seconds


def _read_json(path: Path, default):
    """Read JSON with mtime-aware in-memory cache. Returns default on missing/error."""
    key = str(path)
    now = time.time()
    cached = _FILE_CACHE.get(key)

    if not path.exists():
        return default

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return default

    if cached and cached['mtime'] == mtime and (now - cached['ts']) < FILE_CACHE_TTL:
        return cached['data']

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return cached['data'] if cached else default

    _FILE_CACHE[key] = {'data': data, 'mtime': mtime, 'ts': now}
    return data


# ============================================================
# Last-good-cache for external (sheets) calls
# ============================================================

_EXTERNAL_CACHE: dict[str, dict] = {}
EXTERNAL_CACHE_TTL = 60.0  # seconds — re-fetch sheet data at most once per minute


def _cached_external(key: str, fetch_fn, ttl: float = EXTERNAL_CACHE_TTL):
    """Return cached external data; re-fetch when stale. Falls back to last-good on failure."""
    now = time.time()
    cached = _EXTERNAL_CACHE.get(key)
    if cached and (now - cached['ts']) < ttl:
        return cached['data']
    try:
        data = fetch_fn()
        if data is not None:
            _EXTERNAL_CACHE[key] = {'data': data, 'ts': now}
            return data
    except Exception:
        traceback.print_exc()
    if cached:
        return cached['data']
    return None


# ============================================================
# PH Outreach
# ============================================================

def _today_ph_date() -> date:
    return now_ph().date()


def _today_ph_str() -> str:
    return _today_ph_date().strftime('%Y-%m-%d')


def _count_queue_messages(queue_path: Path) -> int:
    """Count `## N. EMAIL/FB/IG/DM Tn ... Row N` headers in today's queue file."""
    if not queue_path.exists():
        return 0
    try:
        text = queue_path.read_text()
    except OSError:
        return 0
    pattern = re.compile(
        r'^##\s+\d+\.\s+(?:EMAIL|FB|IG|DM)\s+T\d+',
        re.IGNORECASE | re.MULTILINE,
    )
    return len(pattern.findall(text))


def _fetch_ph_outreach():
    """Pull PH outreach stats from the Prospects sheet + today's queue file."""
    today = _today_ph_date()
    today_str = today.strftime('%Y-%m-%d')
    queue_path = TMP_DIR / f'outreach_queue_{today_str}.md'

    queue_size = _count_queue_messages(queue_path)
    queue_mtime_iso = ''
    if queue_path.exists():
        try:
            queue_mtime_iso = datetime.fromtimestamp(
                queue_path.stat().st_mtime, tz=PH_TZ
            ).isoformat()
        except OSError:
            pass

    sent_today = 0
    replies_pending = 0
    followups_due = 0
    last_run = queue_mtime_iso

    sheet_error = None

    try:
        from outreach import load_config, sheets_service, load_env
        from outreach_lifecycle import _read_prospects, detect_followups, _parse_date

        load_env()
        cfg = load_config()
        sid = cfg['spreadsheet_id']
        svc = sheets_service()

        headers, rows = _read_prospects(svc, sid)

        for r in rows:
            status = (r.get('Status') or '').strip().lower()

            # Sent today: any Touch N Date == today
            for t in (1, 2, 3):
                d = _parse_date(r.get(f'Touch {t} Date', ''))
                if d == today:
                    sent_today += 1
                    break

            # Replies pending: status starts with replied_ AND not yet acted on
            # (replied_warm / replied_question are the actionable ones)
            if status in ('replied_warm', 'replied_question', 'replied_other'):
                replies_pending += 1

        wait_rules = cfg.get('limits', {}).get('followup_wait_days', {}) or {
            'touch_1_to_2': 3, 'touch_2_to_3': 5, 'touch_3_to_cold': 7,
        }
        try:
            due = detect_followups(svc, sid, wait_rules, today)
            followups_due = len(due)
        except Exception:
            traceback.print_exc()
            followups_due = 0

    except Exception as e:
        sheet_error = str(e)
        traceback.print_exc()

    # Pick a next action message
    if sheet_error and queue_size == 0:
        next_action = 'No data yet — run `python3 tools/outreach.py queue`'
    elif queue_size > 0 and sent_today == 0:
        next_action = f"Send today's queue ({queue_size} messages waiting)"
    elif followups_due > 0:
        next_action = f'Run `python3 tools/outreach.py followups` ({followups_due} due)'
    elif replies_pending > 0:
        next_action = f'Review {replies_pending} pending reply draft(s)'
    elif sent_today > 0:
        next_action = f'Sent {sent_today} today — done for the day'
    else:
        next_action = 'Generate today\'s queue: `python3 tools/outreach.py queue`'

    return {
        'queue_size': queue_size,
        'sent_today': sent_today,
        'replies_pending': replies_pending,
        'followups_due': followups_due,
        'last_run': last_run,
        'next_action': next_action,
        'error': sheet_error,
    }


# ============================================================
# US Cold Calls
# ============================================================

def _parse_iso_safe(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _fetch_cold_calls():
    """Read cold_call_leads.json and compute pipeline + due-today list."""
    leads = _read_json(COLD_CALL_FILE, [])

    by_status = {'active': 0, 'replied': 0, 'sequence_done': 0}
    followups_due_today = []
    last_sent_dt = None
    now_utc = datetime.now(timezone.utc)

    for lead in leads:
        status = lead.get('status', 'active')
        if status in by_status:
            by_status[status] += 1
        else:
            by_status[status] = by_status.get(status, 0) + 1

        # Track most recent sent timestamp across all leads
        sent = lead.get('sent', {}) or {}
        for ts in sent.values():
            if isinstance(ts, str) and ts.startswith('dry_run:'):
                ts = ts[len('dry_run:'):]
            dt = _parse_iso_safe(ts)
            if dt and (last_sent_dt is None or dt > last_sent_dt):
                last_sent_dt = dt

        if status != 'active':
            continue

        added = _parse_iso_safe(lead.get('added_at', ''))
        if not added:
            continue
        days_since = (now_utc - added).days

        # Find the next due day (first SCHEDULE entry that's <= days_since AND not in sent)
        sent_keys = set(sent.keys())
        for day in COLD_CALL_SCHEDULE:
            if str(day) in sent_keys:
                continue
            if days_since >= day:
                followups_due_today.append({
                    'first_name': lead.get('first_name', ''),
                    'company': lead.get('company', ''),
                    'email': lead.get('email', ''),
                    'day': day,
                })
                break

    active_leads = by_status['active']
    last_sent = last_sent_dt.isoformat() if last_sent_dt else ''

    if not leads:
        next_action = 'No cold-call leads tracked. Add one with `python3 tools/cold_call_followup.py add ...`'
    elif followups_due_today:
        next_action = f'Run `python3 tools/cold_call_followup.py run --send` ({len(followups_due_today)} due)'
    elif active_leads > 0:
        next_action = f'{active_leads} active in sequence — nothing due today'
    else:
        next_action = 'No active sequences. Run more cold calls to add leads.'

    return {
        'active_leads': active_leads,
        'followups_due_today': followups_due_today,
        'by_status': by_status,
        'last_sent': last_sent,
        'next_action': next_action,
    }


# ============================================================
# Content
# ============================================================

def _start_of_week_ph(today: date) -> date:
    """Sunday-start week containing `today` (matches dashboard's weekly stats)."""
    days_since_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_since_sunday)


def _fetch_content():
    """Read content-buffer.json + content_tracker.json. Surface what's ready / next."""
    buffer_data = _read_json(CONTENT_BUFFER_FILE, {})
    tracker = _read_json(CONTENT_TRACKER_FILE, {})

    recordings = buffer_data.get('recordings') or []
    scripts_ready_list = buffer_data.get('scripts_ready') or []
    published_all = buffer_data.get('published') or []

    today = _today_ph_date()
    week_start = _start_of_week_ph(today)
    week_end = week_start + timedelta(days=6)

    published_this_week = 0
    for item in published_all:
        d_str = item.get('date', '')
        try:
            d = datetime.strptime(d_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        if week_start <= d <= week_end:
            published_this_week += 1

    # Find next thing to film: walk tracker.days in date order, return first slot
    # with a topic but filmed != 'done' (filmed in {'pending', '...'})
    next_to_film = None
    days = tracker.get('days') or []
    today_str = today.strftime('%Y-%m-%d')

    # Sort days by date ascending so we surface the soonest pending slot
    def _day_key(day_entry):
        return day_entry.get('date', '9999-99-99')

    for day_entry in sorted(days, key=_day_key):
        day_date = day_entry.get('date', '')
        # Skip days already in the past where nothing was filmed
        # but still surface today/future
        if day_date and day_date < today_str:
            continue
        for slot_name in ('reel_1', 'reel_2', 'youtube'):
            slot = day_entry.get(slot_name) or {}
            topic = (slot.get('topic') or '').strip()
            filmed = (slot.get('filmed') or '').strip().lower()
            if topic and filmed != 'done':
                next_to_film = f"Day {day_entry.get('day', '?')} ({day_date}) {slot_name}: {topic}"
                break
        if next_to_film:
            break

    scripts_ready = len(scripts_ready_list)
    recordings_done = len(recordings)

    if recordings_done > 0:
        next_action = f'Edit + post {recordings_done} recording(s) waiting in buffer'
    elif scripts_ready > 0:
        next_action = f'Film {scripts_ready} script(s) ready to shoot'
    elif next_to_film:
        next_action = f'Write script for next: {next_to_film}'
    elif published_this_week == 0:
        next_action = 'Nothing in buffer — start the week\'s content plan'
    else:
        next_action = f'Posted {published_this_week} this week — keep momentum'

    return {
        'scripts_ready': scripts_ready,
        'recordings_done': recordings_done,
        'published_this_week': published_this_week,
        'next_to_film': next_to_film,
        'next_action': next_action,
    }


# ============================================================
# Routes
# ============================================================

@ops_bp.route('/api/ops/ph-outreach')
def ops_ph_outreach():
    try:
        data = _cached_external('ph_outreach', _fetch_ph_outreach)
        if data is None:
            return jsonify({
                'queue_size': 0, 'sent_today': 0, 'replies_pending': 0,
                'followups_due': 0, 'last_run': '',
                'next_action': 'No data yet — sheet unreachable',
            })
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'queue_size': 0, 'sent_today': 0, 'replies_pending': 0,
            'followups_due': 0, 'last_run': '',
            'next_action': f'Error: {e}',
            'error': str(e),
        }), 500


@ops_bp.route('/api/ops/cold-calls')
def ops_cold_calls():
    try:
        data = _fetch_cold_calls()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'active_leads': 0, 'followups_due_today': [],
            'by_status': {'active': 0, 'replied': 0, 'sequence_done': 0},
            'last_sent': '', 'next_action': f'Error: {e}',
            'error': str(e),
        }), 500


@ops_bp.route('/api/ops/content')
def ops_content():
    try:
        data = _fetch_content()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'scripts_ready': 0, 'recordings_done': 0, 'published_this_week': 0,
            'next_to_film': None, 'next_action': f'Error: {e}',
            'error': str(e),
        }), 500


@ops_bp.route('/api/ops/all')
def ops_all():
    """One-shot fetch of all three systems for the dashboard tile."""
    try:
        ph = _cached_external('ph_outreach', _fetch_ph_outreach) or {
            'queue_size': 0, 'sent_today': 0, 'replies_pending': 0,
            'followups_due': 0, 'last_run': '',
            'next_action': 'No data yet — sheet unreachable',
        }
    except Exception as e:
        traceback.print_exc()
        ph = {'error': str(e), 'next_action': f'Error: {e}'}

    try:
        cc = _fetch_cold_calls()
    except Exception as e:
        traceback.print_exc()
        cc = {'error': str(e), 'next_action': f'Error: {e}'}

    try:
        content = _fetch_content()
    except Exception as e:
        traceback.print_exc()
        content = {'error': str(e), 'next_action': f'Error: {e}'}

    return jsonify({
        'ph_outreach': ph,
        'cold_calls': cc,
        'content': content,
        'ts': now_ph().isoformat(),
    })
