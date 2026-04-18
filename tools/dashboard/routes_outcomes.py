"""
Outcomes routes — Brand > Outcomes panel.

Surfaces the feedback-loop system (outcome_log.jsonl, outcome_summary.json,
workflow_flags.json) as a dashboard UI.

Endpoints:
    GET  /api/brand/outcomes/summary
    GET  /api/brand/outcomes/events?limit=50&action=all
    GET  /api/brand/outcomes/flags
    POST /api/brand/outcomes/flags/<flag_id>/accept
    POST /api/brand/outcomes/flags/<flag_id>/dismiss
"""

import json
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import now_ph

outcomes_bp = Blueprint('outcomes', __name__)

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
TMP_DIR = BASE_DIR / '.tmp'
LOG_FILE = TMP_DIR / 'outcome_log.jsonl'
SUMMARY_FILE = TMP_DIR / 'outcome_summary.json'
FLAGS_FILE = TMP_DIR / 'workflow_flags.json'
SUMMARY_CACHE = TMP_DIR / 'outcomes_summary_cache.json'

CACHE_TTL_SEC = 30


# ============================================================
# Helpers
# ============================================================

def _atomic_write_json(path: Path, data) -> None:
    """Write JSON atomically — temp file + rename — so gunicorn workers never read partial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix='.tmp_', suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def _tail_jsonl(path: Path, limit: int):
    """Return last N parsed JSON lines from a JSONL file (newest last)."""
    if not path.exists():
        return []
    try:
        # For append-only logs this size is fine to read whole — file grows slowly.
        lines = path.read_text().splitlines()
    except OSError:
        return []
    parsed = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if limit and len(parsed) > limit:
        return parsed[-limit:]
    return parsed


def _cache_is_fresh() -> bool:
    if not SUMMARY_CACHE.exists():
        return False
    try:
        age = now_ph().timestamp() - SUMMARY_CACHE.stat().st_mtime
        return age < CACHE_TTL_SEC
    except OSError:
        return False


# ============================================================
# Endpoints
# ============================================================

@outcomes_bp.route('/api/brand/outcomes/summary')
def api_outcomes_summary():
    """Return the rolled-up outcome summary. 30s disk cache."""
    # Cache hit
    if _cache_is_fresh():
        cached = _read_json(SUMMARY_CACHE)
        if cached is not None:
            return jsonify(cached)

    if not SUMMARY_FILE.exists():
        payload = {
            'ok': True,
            'exists': False,
            'reason': 'Summary not generated yet. Run: python3 tools/check_outcomes.py',
        }
        try:
            _atomic_write_json(SUMMARY_CACHE, payload)
        except OSError:
            pass
        return jsonify(payload)

    raw = _read_json(SUMMARY_FILE, default={})
    payload = {'ok': True, 'exists': True, **raw}

    try:
        _atomic_write_json(SUMMARY_CACHE, payload)
    except OSError:
        pass

    return jsonify(payload)


@outcomes_bp.route('/api/brand/outcomes/events')
def api_outcomes_events():
    """Tail recent outcome events."""
    try:
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 500))
    action_filter = (request.args.get('action') or 'all').strip().lower()

    events = _tail_jsonl(LOG_FILE, limit * 4 if action_filter != 'all' else limit)

    if action_filter and action_filter != 'all':
        events = [e for e in events if (e.get('action') or '').lower() == action_filter]

    # Reverse so newest first for display
    events = events[-limit:]
    events_desc = list(reversed(events))

    # Total count (unfiltered) — cheap since file is small
    total_count = 0
    if LOG_FILE.exists():
        try:
            total_count = sum(1 for line in LOG_FILE.read_text().splitlines() if line.strip())
        except OSError:
            total_count = 0

    return jsonify({
        'ok': True,
        'events': events_desc,
        'total_count': total_count,
    })


@outcomes_bp.route('/api/brand/outcomes/flags')
def api_outcomes_flags():
    """Return pending workflow flags."""
    raw = _read_json(FLAGS_FILE, default=None)

    # Accept either {flags: [...]} or bare [...] formats (check_outcomes.py writes the list).
    flags = []
    if isinstance(raw, list):
        flags = raw
    elif isinstance(raw, dict):
        flags = raw.get('flags', [])

    pending = [f for f in flags if (f.get('status') or 'pending') == 'pending']
    return jsonify({
        'ok': True,
        'flags': pending,
        'count': len(pending),
    })


def _update_flag_status(flag_id: str, new_status: str, ts_field: str):
    raw = _read_json(FLAGS_FILE, default=None)
    if raw is None:
        return None, 'Flags file not found'

    # Normalize shape — preserve shape on write.
    wrapped = isinstance(raw, dict)
    flags = raw.get('flags', []) if wrapped else raw

    target = None
    for f in flags:
        if f.get('id') == flag_id:
            target = f
            break

    if target is None:
        return None, f'Flag {flag_id} not found'

    target['status'] = new_status
    target[ts_field] = now_ph().isoformat(timespec='seconds')

    to_write = {'flags': flags} if wrapped else flags
    _atomic_write_json(FLAGS_FILE, to_write)
    return target, None


@outcomes_bp.route('/api/brand/outcomes/flags/<flag_id>/accept', methods=['POST'])
def api_outcomes_flag_accept(flag_id):
    try:
        flag, err = _update_flag_status(flag_id, 'accepted', 'accepted_at')
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    if err:
        return jsonify({'ok': False, 'error': err}), 404
    return jsonify({'ok': True, 'flag_id': flag_id})


@outcomes_bp.route('/api/brand/outcomes/flags/<flag_id>/dismiss', methods=['POST'])
def api_outcomes_flag_dismiss(flag_id):
    try:
        flag, err = _update_flag_status(flag_id, 'dismissed', 'dismissed_at')
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    if err:
        return jsonify({'ok': False, 'error': err}), 404
    return jsonify({'ok': True, 'flag_id': flag_id})
