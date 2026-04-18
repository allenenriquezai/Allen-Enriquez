"""
Today routes — landing tab aggregating action queue, goals, and journal.

Three pills:
- Queue: top-10 ranked action items across outreach, cold-calls, EPS, content, workflow flags
- Goals: read/write projects/personal/goals/current.md
- Journal: read/write projects/personal/journal/YYYY-MM-DD.md (structured markdown)

Registration (done by orchestrator in app.py):
    from routes_today import today_bp
    app.register_blueprint(today_bp)
"""

import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import now_ph, today_ph

today_bp = Blueprint('today', __name__)

# Add tools/ to path so we can reuse routes_ops helpers
sys.path.insert(0, str(Path(__file__).parent))

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/

# Personal data
PERSONAL_DIR = BASE_DIR / 'projects' / 'personal'
GOALS_FILE = PERSONAL_DIR / 'goals' / 'current.md'
JOURNAL_DIR = PERSONAL_DIR / 'journal'
PERSONAL_TMP = PERSONAL_DIR / '.tmp'
CONTENT_TRACKER_FILE = PERSONAL_TMP / 'content_tracker.json'

# Repo-root workflow flags
WORKFLOW_FLAGS_FILE = BASE_DIR / '.tmp' / 'workflow_flags.json'

# EPS brief disk cache (written by routes_brief.py)
EPS_BRIEF_CACHE = BASE_DIR / '.tmp' / 'brief_cache' / 'eps.json'

PH_TZ = timezone(timedelta(hours=8))


# ============================================================
# Helpers — read JSON / file safely
# ============================================================

def _read_json(path: Path, default):
    """Read JSON, return default on missing/error."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return default


def _mtime_iso(path: Path):
    if not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=PH_TZ).isoformat()
    except OSError:
        return None


# ============================================================
# Queue item collectors
# ============================================================

def _collect_workflow_flags():
    """Pending workflow flags → priority 90."""
    flags = _read_json(WORKFLOW_FLAGS_FILE, [])
    if not isinstance(flags, list):
        return []
    pending = [f for f in flags if (f.get('status') or '').lower() == 'pending']
    if not pending:
        return []
    # One row summarising total pending flags
    count = len(pending)
    first = pending[0]
    pattern = (first.get('pattern') or 'workflow update')[:60]
    return [{
        'id': f'workflow_flags:{count}',
        'domain': 'workflow',
        'icon': '🚩',
        'title': f'{count} workflow update{"s" if count != 1 else ""} pending',
        'context': pattern,
        'cta': 'workflow-flags',
        'priority': 90,
    }]


def _collect_outreach():
    """PH outreach: replies waiting (85), followups due (75), queue to send (70)."""
    items = []
    try:
        from routes_ops import _fetch_ph_outreach
        ph = _fetch_ph_outreach() or {}
    except Exception:
        traceback.print_exc()
        return items

    replies_pending = int(ph.get('replies_pending') or 0)
    followups_due = int(ph.get('followups_due') or 0)
    queue_size = int(ph.get('queue_size') or 0)
    sent_today = int(ph.get('sent_today') or 0)

    if replies_pending > 0:
        items.append({
            'id': f'reply:ph:{replies_pending}',
            'domain': 'reply',
            'icon': '💬',
            'title': f'{replies_pending} repl{"ies" if replies_pending != 1 else "y"} waiting',
            'context': 'PH outreach — warm/question replies to handle',
            'cta': 'outreach',
            'priority': 85,
        })

    if followups_due > 0:
        items.append({
            'id': f'outreach_followups:{followups_due}',
            'domain': 'outreach',
            'icon': '📬',
            'title': f'{followups_due} follow-up{"s" if followups_due != 1 else ""} due',
            'context': 'Run: python3 tools/outreach.py followups',
            'cta': 'outreach',
            'priority': 75,
        })

    if queue_size > 0 and sent_today == 0:
        items.append({
            'id': f'outreach_queue:{queue_size}',
            'domain': 'outreach',
            'icon': '📬',
            'title': f"Send today's queue ({queue_size} messages)",
            'context': f'{queue_size} drafted, 0 sent today',
            'cta': 'outreach',
            'priority': 70,
        })

    return items


def _collect_cold_calls():
    """Cold call follow-ups due today → priority 80 per lead (cap 3)."""
    items = []
    try:
        from routes_ops import _fetch_cold_calls
        cc = _fetch_cold_calls() or {}
    except Exception:
        traceback.print_exc()
        return items

    due = cc.get('followups_due_today') or []
    for lead in due[:3]:
        fn = (lead.get('first_name') or '').strip() or 'Lead'
        company = (lead.get('company') or '').strip()
        day = lead.get('day', '?')
        title = f'Cold call follow-up: {fn}'
        context = f'{company} — day {day} of sequence'[:60] if company else f'Day {day} of sequence'
        key = (lead.get('email') or '').strip().lower() or f'{fn}:{company}'
        items.append({
            'id': f'cold_call:{key}:{day}',
            'domain': 'cold-call',
            'icon': '📞',
            'title': title,
            'context': context,
            'cta': 'cold-calls',
            'priority': 80,
        })
    return items


def _collect_eps():
    """EPS activities overdue → priority 65 (single row). Reads brief disk cache."""
    cache = _read_json(EPS_BRIEF_CACHE, None)
    if not cache or not isinstance(cache, dict):
        return []
    data = cache.get('data') or {}
    activities = data.get('activities') or {}
    overdue = 0
    for tier in ('tier1', 'tier2', 'other'):
        for act in activities.get(tier, []) or []:
            if act.get('overdue'):
                overdue += 1
    if overdue == 0:
        return []
    return [{
        'id': f'eps_overdue:{overdue}',
        'domain': 'eps',
        'icon': '💼',
        'title': f'{overdue} EPS activit{"ies" if overdue != 1 else "y"} overdue',
        'context': 'Clear in Pipedrive — oldest first',
        'cta': 'eps',
        'priority': 65,
    }]


def _collect_content():
    """Content tasks for today → priority 50."""
    tracker = _read_json(CONTENT_TRACKER_FILE, {})
    if not tracker:
        return []
    days = tracker.get('days') or []
    today_str = today_ph()
    pending_today = []
    for day_entry in days:
        if day_entry.get('date') != today_str:
            continue
        for slot_name in ('reel_1', 'reel_2', 'youtube'):
            slot = day_entry.get(slot_name) or {}
            topic = (slot.get('topic') or '').strip()
            posted = (slot.get('posted') or '').strip().lower()
            if topic and posted != 'posted':
                pending_today.append((slot_name, topic))
    if not pending_today:
        return []
    slot_name, topic = pending_today[0]
    count = len(pending_today)
    title = f'{count} content task{"s" if count != 1 else ""} today'
    context = f'{slot_name}: {topic}'[:60]
    return [{
        'id': f'content:{today_str}:{count}',
        'domain': 'content',
        'icon': '🎬',
        'title': title,
        'context': context,
        'cta': 'content',
        'priority': 50,
    }]


# ============================================================
# Queue counts (for header chips)
# ============================================================

def _build_counts(items):
    counts = {'outreach': 0, 'cold_call': 0, 'eps': 0, 'content': 0, 'workflow': 0}
    for it in items:
        dom = it.get('domain', '')
        if dom == 'outreach' or dom == 'reply':
            counts['outreach'] += 1
        elif dom == 'cold-call':
            counts['cold_call'] += 1
        elif dom == 'eps':
            counts['eps'] += 1
        elif dom == 'content':
            counts['content'] += 1
        elif dom == 'workflow':
            counts['workflow'] += 1
    return counts


# ============================================================
# Journal helpers
# ============================================================

def _journal_path(date_str: str) -> Path:
    return JOURNAL_DIR / f'{date_str}.md'


def _parse_date_str(date_str: str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _render_journal(date_str: str, wins, lesson, tomorrow, mood):
    lines = ['---', f'date: {date_str}']
    if mood:
        lines.append(f'mood: {mood}')
    lines.append('---')
    lines.append('')
    lines.append('## Wins')
    for w in (wins or []):
        lines.append(f'- {w}')
    lines.append('')
    lines.append('## Lesson')
    lines.append(lesson or '')
    lines.append('')
    lines.append('## Tomorrow top 3')
    for i, t in enumerate((tomorrow or [])[:3], start=1):
        lines.append(f'{i}. {t}')
    lines.append('')
    return '\n'.join(lines)


# ============================================================
# Routes — Queue
# ============================================================

_QUEUE_CACHE_FILE = BASE_DIR / '.tmp' / 'today_queue_cache.json'
_QUEUE_TTL = 60.0  # seconds — repeat loads are instant within this window


def _queue_cache_read():
    """Return cached payload if fresh, else None. Disk-backed so gunicorn workers share."""
    import time
    try:
        if not _QUEUE_CACHE_FILE.exists():
            return None
        age = time.time() - _QUEUE_CACHE_FILE.stat().st_mtime
        if age >= _QUEUE_TTL:
            return None
        return json.loads(_QUEUE_CACHE_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _queue_cache_write(payload):
    try:
        _QUEUE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _QUEUE_CACHE_FILE.write_text(json.dumps(payload), encoding='utf-8')
    except OSError:
        pass  # cache is best-effort


@today_bp.route('/api/today/queue', methods=['GET'])
def api_today_queue():
    force = request.args.get('refresh') == '1'
    if not force:
        cached = _queue_cache_read()
        if cached is not None:
            return jsonify(cached)
    try:
        items = []
        items.extend(_collect_workflow_flags())
        items.extend(_collect_outreach())
        items.extend(_collect_cold_calls())
        items.extend(_collect_eps())
        items.extend(_collect_content())

        items.sort(key=lambda x: (-int(x.get('priority', 0)), x.get('domain', '')))
        items = items[:10]

        counts = _build_counts(items)
        payload = {'ok': True, 'items': items, 'counts': counts, 'cached_at': datetime.now(PH_TZ).isoformat()}
        _queue_cache_write(payload)
        return jsonify(payload)
    except Exception as e:
        traceback.print_exc()
        # Serve stale cache on error so UI never goes blank
        if _QUEUE_CACHE_FILE.exists():
            try:
                return jsonify(json.loads(_QUEUE_CACHE_FILE.read_text(encoding='utf-8')))
            except (OSError, json.JSONDecodeError):
                pass
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Routes — Goals
# ============================================================

@today_bp.route('/api/today/goals', methods=['GET'])
def api_today_goals_get():
    try:
        if not GOALS_FILE.exists():
            return jsonify({
                'ok': True,
                'exists': False,
                'raw': '',
                'last_modified': None,
            })
        raw = GOALS_FILE.read_text(encoding='utf-8')
        return jsonify({
            'ok': True,
            'exists': True,
            'raw': raw,
            'last_modified': _mtime_iso(GOALS_FILE),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@today_bp.route('/api/today/goals', methods=['POST'])
def api_today_goals_post():
    try:
        data = request.get_json(silent=True) or {}
        raw = data.get('raw', '')
        if not isinstance(raw, str):
            return jsonify({'ok': False, 'error': 'raw_must_be_string'}), 400
        GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        GOALS_FILE.write_text(raw, encoding='utf-8')
        return jsonify({
            'ok': True,
            'last_modified': _mtime_iso(GOALS_FILE),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Routes — Journal
# ============================================================

@today_bp.route('/api/today/journal', methods=['GET'])
def api_today_journal_get():
    try:
        date_str = (request.args.get('date') or '').strip() or today_ph()
        parsed = _parse_date_str(date_str)
        if not parsed:
            return jsonify({'ok': False, 'error': 'invalid_date'}), 400

        path = _journal_path(date_str)
        exists = path.exists()
        raw = path.read_text(encoding='utf-8') if exists else ''

        # Yesterday info
        y_date = (parsed - timedelta(days=1)).strftime('%Y-%m-%d')
        y_path = _journal_path(y_date)
        y_exists = y_path.exists()
        y_preview = ''
        if y_exists:
            try:
                y_raw = y_path.read_text(encoding='utf-8')
                y_preview = y_raw[:200]
            except OSError:
                y_preview = ''

        return jsonify({
            'ok': True,
            'date': date_str,
            'exists': exists,
            'raw': raw,
            'yesterday': {
                'date': y_date,
                'exists': y_exists,
                'preview': y_preview,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@today_bp.route('/api/today/journal', methods=['POST'])
def api_today_journal_post():
    try:
        data = request.get_json(silent=True) or {}
        date_str = (data.get('date') or '').strip() or today_ph()
        if not _parse_date_str(date_str):
            return jsonify({'ok': False, 'error': 'invalid_date'}), 400

        wins = data.get('wins') or []
        lesson = data.get('lesson') or ''
        tomorrow = data.get('tomorrow') or []
        mood = data.get('mood') or ''

        if not isinstance(wins, list):
            return jsonify({'ok': False, 'error': 'wins_must_be_list'}), 400
        if not isinstance(tomorrow, list):
            return jsonify({'ok': False, 'error': 'tomorrow_must_be_list'}), 400
        if not isinstance(lesson, str):
            return jsonify({'ok': False, 'error': 'lesson_must_be_string'}), 400

        content = _render_journal(date_str, wins, lesson, tomorrow, mood)
        path = _journal_path(date_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

        return jsonify({'ok': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500
