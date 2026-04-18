"""
Content Script Bank — scripts + calendar endpoints for the Brand > Content sub-pill.

Canonical storage: projects/personal/content/scripts/*.md with YAML frontmatter:

    ---
    title: Hook title
    status: idea|scripted|recorded|edited|posted
    platform: reel|youtube|carousel
    hook: one-liner
    created: 2026-04-18
    posted: 2026-04-20
    scheduled: 2026-04-22
    ---
    body markdown

Legacy fallback: projects/personal/.tmp/content_tracker.json (30-day Hormozi tracker).

Endpoints:
    GET    /api/brand/content/scripts
    GET    /api/brand/content/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD
    POST   /api/brand/content/scripts
    PATCH  /api/brand/content/scripts/<filename>
"""

from __future__ import annotations

import json
import re
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from flask import Blueprint, jsonify, request

from config import now_ph

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

content_bp = Blueprint('content', __name__)

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
SCRIPTS_DIR = BASE_DIR / 'projects' / 'personal' / 'content' / 'scripts'
LEGACY_TRACKER = BASE_DIR / 'projects' / 'personal' / '.tmp' / 'content_tracker.json'
CACHE_FILE = BASE_DIR / '.tmp' / 'content_scripts_cache.json'
CACHE_TTL = 30.0

STATUS_ORDER = {'idea': 0, 'scripted': 1, 'recorded': 2, 'edited': 3, 'posted': 4}
VALID_STATUSES = set(STATUS_ORDER.keys())
VALID_PLATFORMS = {'reel', 'youtube', 'carousel'}
NEXT_STATUS = {'idea': 'scripted', 'scripted': 'recorded', 'recorded': 'edited', 'edited': 'posted', 'posted': 'posted'}


# ============================================================
# Frontmatter parsing
# ============================================================

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split `---\\n...\\n---\\nbody`. Return (meta_dict, body). Empty dict if no frontmatter."""
    if not text.startswith('---'):
        return {}, text
    parts = text.split('---\n', 2)
    if len(parts) < 3:
        return {}, text
    _, fm_raw, body = parts
    if HAS_YAML:
        try:
            meta = yaml.safe_load(fm_raw) or {}
            if not isinstance(meta, dict):
                meta = {}
        except Exception:
            meta = _tiny_frontmatter(fm_raw)
    else:
        meta = _tiny_frontmatter(fm_raw)
    return meta, body


def _tiny_frontmatter(raw: str) -> dict:
    """Fallback KEY: VALUE line parser when yaml unavailable."""
    meta = {}
    for line in raw.splitlines():
        m = re.match(r'^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$', line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        meta[key] = val
    return meta


def _dump_frontmatter(meta: dict, body: str) -> str:
    """Write frontmatter + body to markdown."""
    if HAS_YAML:
        fm = yaml.safe_dump(meta, default_flow_style=False, sort_keys=False).strip()
    else:
        fm_lines = []
        for k, v in meta.items():
            if v is None:
                continue
            fm_lines.append(f'{k}: {v}')
        fm = '\n'.join(fm_lines)
    body = body if body.startswith('\n') else '\n' + body
    return f'---\n{fm}\n---{body}'


def _slugify(title: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', title or 'untitled').strip().lower()
    s = re.sub(r'[\s_-]+', '-', s)
    return (s[:60] or 'untitled').strip('-')


# ============================================================
# Disk cache (gunicorn-safe)
# ============================================================

def _cache_read():
    try:
        if not CACHE_FILE.exists():
            return None
        if (time.time() - CACHE_FILE.stat().st_mtime) >= CACHE_TTL:
            return None
        return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_write(payload):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(payload), encoding='utf-8')
    except OSError:
        pass


def _cache_invalidate():
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
    except OSError:
        pass


# ============================================================
# Script collection
# ============================================================

def _read_script_file(path: Path):
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None
    meta, body = _parse_frontmatter(text)
    body_clean = body.strip()
    preview = body_clean[:200] + ('...' if len(body_clean) > 200 else '')
    status = (meta.get('status') or 'idea').lower()
    if status not in VALID_STATUSES:
        status = 'idea'
    platform = (meta.get('platform') or 'reel').lower()
    if platform not in VALID_PLATFORMS:
        platform = 'reel'
    return {
        'filename': path.name,
        'title': meta.get('title') or path.stem,
        'status': status,
        'platform': platform,
        'hook': meta.get('hook') or '',
        'created': str(meta.get('created') or ''),
        'posted': str(meta.get('posted') or ''),
        'scheduled': str(meta.get('scheduled') or ''),
        'body_preview': preview,
        'body': body_clean,
        'path': str(path),
        'source': 'markdown',
    }


def _collect_markdown_scripts() -> list[dict]:
    if not SCRIPTS_DIR.exists():
        return []
    out = []
    for p in SCRIPTS_DIR.glob('*.md'):
        row = _read_script_file(p)
        if row:
            out.append(row)
    return out


def _collect_legacy_scripts() -> list[dict]:
    """Map content_tracker.json days/slots into script-shaped dicts."""
    if not LEGACY_TRACKER.exists():
        return []
    try:
        tracker = json.loads(LEGACY_TRACKER.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for day in (tracker.get('days') or []):
        day_date = day.get('date', '')
        day_num = day.get('day', '?')
        for slot in ('reel_1', 'reel_2', 'youtube'):
            s = day.get(slot) or {}
            topic = (s.get('topic') or '').strip()
            if not topic:
                continue
            posted_flag = (s.get('posted') or '').strip().lower()
            filmed_flag = (s.get('filmed') or '').strip().lower()
            script_flag = (s.get('script') or '').strip().lower()
            if posted_flag == 'posted':
                status = 'posted'
            elif filmed_flag == 'done':
                status = 'edited'
            elif script_flag == 'done':
                status = 'scripted'
            else:
                status = 'idea'
            platform = 'youtube' if slot == 'youtube' else 'reel'
            out.append({
                'filename': f'legacy-day{day_num}-{slot}',
                'title': topic,
                'status': status,
                'platform': platform,
                'hook': '',
                'created': day_date,
                'posted': day_date if status == 'posted' else '',
                'scheduled': day_date if status != 'posted' else '',
                'body_preview': f'[legacy tracker Day {day_num} / {slot}]',
                'body': '',
                'path': str(LEGACY_TRACKER),
                'source': 'legacy',
            })
    return out


def _sort_scripts(scripts: list[dict]) -> list[dict]:
    def key(s):
        return (STATUS_ORDER.get(s['status'], 99), -_date_rank(s.get('created')))
    return sorted(scripts, key=key)


def _date_rank(s: str) -> int:
    try:
        return int(datetime.strptime(s, '%Y-%m-%d').timestamp())
    except (ValueError, TypeError):
        return 0


def _build_counts(scripts: list[dict]) -> dict:
    by_status = {k: 0 for k in STATUS_ORDER}
    by_platform = {k: 0 for k in VALID_PLATFORMS}
    for s in scripts:
        by_status[s['status']] = by_status.get(s['status'], 0) + 1
        by_platform[s['platform']] = by_platform.get(s['platform'], 0) + 1
    return {'by_status': by_status, 'by_platform': by_platform}


def _load_all_scripts(use_cache: bool = True) -> dict:
    if use_cache:
        cached = _cache_read()
        if cached is not None:
            return cached
    md = _collect_markdown_scripts()
    if not md:
        legacy = _collect_legacy_scripts()
        scripts = _sort_scripts(legacy)
    else:
        scripts = _sort_scripts(md)
    payload = {'ok': True, 'scripts': scripts, 'counts': _build_counts(scripts)}
    _cache_write(payload)
    return payload


# ============================================================
# Routes
# ============================================================

@content_bp.route('/api/brand/content/scripts', methods=['GET'])
def list_scripts():
    try:
        force = request.args.get('refresh') == '1'
        return jsonify(_load_all_scripts(use_cache=not force))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e), 'scripts': [], 'counts': {}}), 500


@content_bp.route('/api/brand/content/calendar', methods=['GET'])
def calendar():
    try:
        today = now_ph().date()
        # Default: this week (Sun-start) + next week
        days_since_sun = (today.weekday() + 1) % 7
        default_from = today - timedelta(days=days_since_sun)
        default_to = default_from + timedelta(days=13)

        from_s = request.args.get('from')
        to_s = request.args.get('to')
        try:
            d_from = datetime.strptime(from_s, '%Y-%m-%d').date() if from_s else default_from
        except ValueError:
            d_from = default_from
        try:
            d_to = datetime.strptime(to_s, '%Y-%m-%d').date() if to_s else default_to
        except ValueError:
            d_to = default_to

        scripts = _load_all_scripts(use_cache=True).get('scripts', [])

        # Bucket per day
        buckets: dict[str, list[dict]] = {}
        d = d_from
        while d <= d_to:
            buckets[d.strftime('%Y-%m-%d')] = []
            d += timedelta(days=1)

        for s in scripts:
            target = None
            if s['status'] == 'posted' and s.get('posted'):
                target = s['posted']
            elif s['status'] != 'posted' and s.get('scheduled'):
                target = s['scheduled']
            if not target or target not in buckets:
                continue
            buckets[target].append({
                'title': s['title'],
                'status': s['status'],
                'platform': s['platform'],
                'filename': s['filename'],
            })

        days = [{'date': k, 'items': v} for k, v in sorted(buckets.items())]
        return jsonify({'ok': True, 'days': days})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e), 'days': []}), 500


@content_bp.route('/api/brand/content/scripts', methods=['POST'])
def create_script():
    try:
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'ok': False, 'error': 'title required'}), 400
        status = (data.get('status') or 'idea').lower()
        if status not in VALID_STATUSES:
            status = 'idea'
        platform = (data.get('platform') or 'reel').lower()
        if platform not in VALID_PLATFORMS:
            platform = 'reel'
        hook = (data.get('hook') or '').strip()
        body = data.get('body') or ''

        today_str = now_ph().date().strftime('%Y-%m-%d')
        slug = _slugify(title)
        filename = f'{today_str}-{slug}.md'
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCRIPTS_DIR / filename
        # Avoid overwrite
        n = 2
        while path.exists():
            path = SCRIPTS_DIR / f'{today_str}-{slug}-{n}.md'
            n += 1

        meta = {
            'title': title,
            'status': status,
            'platform': platform,
            'hook': hook,
            'created': today_str,
        }
        path.write_text(_dump_frontmatter(meta, body), encoding='utf-8')
        _cache_invalidate()
        return jsonify({'ok': True, 'path': str(path), 'filename': path.name})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@content_bp.route('/api/brand/content/scripts/<filename>', methods=['PATCH'])
def patch_script(filename):
    try:
        # Safety — no path traversal
        if '/' in filename or '\\' in filename or not filename.endswith('.md'):
            return jsonify({'ok': False, 'error': 'invalid filename'}), 400
        path = SCRIPTS_DIR / filename
        if not path.exists():
            return jsonify({'ok': False, 'error': 'not found'}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict) or not data:
            return jsonify({'ok': False, 'error': 'empty body'}), 400

        text = path.read_text(encoding='utf-8')
        meta, body = _parse_frontmatter(text)

        for key, val in data.items():
            if key == 'body':
                body = val if isinstance(val, str) else body
                continue
            if key == 'status':
                val = (val or '').lower()
                if val not in VALID_STATUSES:
                    continue
                # Auto-stamp posted date when transitioning to posted
                if val == 'posted' and not meta.get('posted'):
                    meta['posted'] = now_ph().date().strftime('%Y-%m-%d')
            if key == 'platform':
                val = (val or '').lower()
                if val not in VALID_PLATFORMS:
                    continue
            meta[key] = val

        path.write_text(_dump_frontmatter(meta, body), encoding='utf-8')
        _cache_invalidate()
        return jsonify({'ok': True, 'filename': filename})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500
