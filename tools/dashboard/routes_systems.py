"""
Systems routes — live automation + service health for the "Systems" panel under Brand tab.

Surfaces plist-based automation status (via launchctl) + on-disk freshness signals
for external services. No network calls — must load in <500ms.

Registration (orchestrator handles this):
    from routes_systems import systems_bp
    app.register_blueprint(systems_bp)

Endpoints:
    GET  /api/brand/systems/automations
    GET  /api/brand/systems/automations/<label>/log
    POST /api/brand/systems/automations/<label>/run
    GET  /api/brand/systems/services
"""

import json
import plistlib
import subprocess
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify

from config import now_ph

systems_bp = Blueprint('systems', __name__)

PH_TZ = timezone(timedelta(hours=8))

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
AUTOMATION_DIR = BASE_DIR / 'automation'
TMP_ROOT = BASE_DIR / '.tmp'
PERSONAL_TMP = BASE_DIR / 'projects' / 'personal' / '.tmp'
EPS_TMP = BASE_DIR / 'projects' / 'eps' / '.tmp'

OUTCOME_LOG = TMP_ROOT / 'outcome_log.jsonl'
BRIEF_CACHE_DIR = TMP_ROOT / 'brief_cache'
CONTENT_BUFFER = PERSONAL_TMP / 'content-buffer.json'

WEEKDAY_MAP = {
    0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
    4: 'Thursday', 5: 'Friday', 6: 'Saturday',
}


# ============================================================
# Helpers
# ============================================================

def _iso_ph(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=PH_TZ).isoformat()


def _mtime(path: Path):
    try:
        return path.stat().st_mtime
    except (OSError, AttributeError):
        return None


def _friendly_name(label: str) -> str:
    name = label
    if name.startswith('com.enriquezOS.'):
        name = name[len('com.enriquezOS.'):]
    return name.replace('-', ' ').replace('_', ' ').title()


def _format_schedule(plist_data: dict) -> str:
    interval = plist_data.get('StartInterval')
    if isinstance(interval, int):
        if interval % 3600 == 0:
            h = interval // 3600
            return f'every {h} hour' + ('s' if h != 1 else '')
        if interval % 60 == 0:
            m = interval // 60
            return f'every {m} minute' + ('s' if m != 1 else '')
        return f'every {interval} seconds'

    cal = plist_data.get('StartCalendarInterval')
    if isinstance(cal, dict):
        hour = cal.get('Hour')
        minute = cal.get('Minute', 0)
        weekday = cal.get('Weekday')
        day = cal.get('Day')
        if hour is not None:
            hh_mm = f'{hour:02d}:{minute:02d}'
            if weekday is not None:
                return f'weekly {WEEKDAY_MAP.get(weekday, f"day{weekday}")} {hh_mm}'
            if day is not None:
                return f'monthly day {day} {hh_mm}'
            return f'daily {hh_mm}'
        return str(cal)
    if isinstance(cal, list):
        return f'{len(cal)} scheduled windows'

    return 'on demand'


def _label_to_sh(label: str) -> Path:
    """com.enriquezOS.ph-outreach-daily -> automation/run_ph_outreach_daily.sh"""
    name = label
    if name.startswith('com.enriquezOS.'):
        name = name[len('com.enriquezOS.'):]
    slug = name.replace('-', '_')
    return AUTOMATION_DIR / f'run_{slug}.sh'


def _launchctl_status(label: str) -> dict:
    """Return {'loaded': bool, 'pid': int|None, 'last_exit_code': int|None}."""
    try:
        proc = subprocess.run(
            ['/bin/launchctl', 'list', label],
            capture_output=True, text=True, timeout=3,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {'loaded': False, 'pid': None, 'last_exit_code': None}

    if proc.returncode != 0:
        return {'loaded': False, 'pid': None, 'last_exit_code': None}

    # Output is a plist-like dict: { "PID" = 1234; "LastExitStatus" = 0; "Label" = "..."; };
    pid = None
    exit_code = None
    for line in proc.stdout.splitlines():
        s = line.strip().rstrip(';').strip()
        if s.startswith('"PID"') and '=' in s:
            try:
                pid = int(s.split('=', 1)[1].strip())
            except ValueError:
                pid = None
        elif s.startswith('"LastExitStatus"') and '=' in s:
            try:
                exit_code = int(s.split('=', 1)[1].strip())
            except ValueError:
                exit_code = None
    return {'loaded': True, 'pid': pid, 'last_exit_code': exit_code}


def _derive_status(loaded: bool, pid, exit_code, has_log: bool) -> str:
    if not loaded:
        return 'never' if not has_log else 'loaded'
    if pid is not None:
        return 'loaded'
    if exit_code is None:
        return 'never' if not has_log else 'loaded'
    return 'success' if exit_code == 0 else 'fail'


def _parse_plist(plist_path: Path) -> dict:
    with open(plist_path, 'rb') as f:
        return plistlib.load(f)


def _build_automation_entry(plist_path: Path) -> dict:
    data = _parse_plist(plist_path)
    label = data.get('Label', plist_path.stem)
    stdout_path = data.get('StandardOutPath') or ''
    stderr_path = data.get('StandardErrorPath') or ''

    # Prefer stdout, fall back to stderr
    log_path = stdout_path or stderr_path
    log_p = Path(log_path) if log_path else None

    last_run_ts = _mtime(log_p) if log_p else None
    # Consider stderr too if stdout is missing/older
    if log_p and stderr_path and stderr_path != stdout_path:
        err_ts = _mtime(Path(stderr_path))
        if err_ts and (last_run_ts is None or err_ts > last_run_ts):
            last_run_ts = err_ts
            log_path = stderr_path

    status_info = _launchctl_status(label)
    status = _derive_status(
        status_info['loaded'],
        status_info['pid'],
        status_info['last_exit_code'],
        has_log=last_run_ts is not None,
    )

    sh_path = _label_to_sh(label)
    sh_str = str(sh_path) if sh_path.exists() else None

    return {
        'label': label,
        'friendly_name': _friendly_name(label),
        'last_run': _iso_ph(last_run_ts) if last_run_ts else None,
        'last_exit_code': status_info['last_exit_code'],
        'status': status,
        'schedule': _format_schedule(data),
        'log_path': log_path or None,
        'plist_path': str(plist_path),
        'sh_path': sh_str,
    }


def _find_plist_for_label(label: str):
    for p in sorted(AUTOMATION_DIR.glob('*.plist')):
        try:
            data = _parse_plist(p)
        except Exception:
            continue
        if data.get('Label') == label:
            return p, data
    return None, None


def _tail(path: Path, n: int = 50) -> str:
    try:
        with open(path, 'rb') as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                chunk = min(size, 64 * 1024)
                f.seek(size - chunk, 0)
                data = f.read().decode('utf-8', errors='replace')
            except OSError:
                f.seek(0)
                data = f.read().decode('utf-8', errors='replace')
        lines = data.splitlines()
        return '\n'.join(lines[-n:])
    except (OSError, FileNotFoundError):
        return ''


# ============================================================
# Service health helpers
# ============================================================

def _age_status(mtime: float, green_max_s: float, yellow_max_s: float) -> tuple:
    """Return (status, detail_age_str)."""
    if mtime is None:
        return 'unknown', 'no signal'
    age = max(0.0, datetime.now().timestamp() - mtime)
    detail = _humanize_age(age)
    if age < green_max_s:
        return 'green', detail
    if age < yellow_max_s:
        return 'yellow', detail
    return 'red', detail


def _humanize_age(seconds: float) -> str:
    if seconds < 60:
        return f'{int(seconds)}s ago'
    if seconds < 3600:
        return f'{int(seconds // 60)}m ago'
    if seconds < 86400:
        return f'{int(seconds // 3600)}h ago'
    return f'{int(seconds // 86400)}d ago'


def _latest_match(directory: Path, glob: str):
    """Return path of newest file matching glob, or None."""
    try:
        matches = list(directory.glob(glob))
    except OSError:
        return None
    if not matches:
        return None
    matches.sort(key=lambda p: _mtime(p) or 0, reverse=True)
    return matches[0]


def _svc_eps_cache(name: str) -> dict:
    """Pipedrive / ServiceM8 — mtime of brief_cache/eps.json."""
    path = BRIEF_CACHE_DIR / 'eps.json'
    mt = _mtime(path)
    if mt is None:
        return {
            'name': name, 'status': 'unknown',
            'detail': 'No brief cache yet — run /brief or wait for morning briefing',
            'last_ok': None,
        }
    status, age_str = _age_status(mt, 15 * 60, 2 * 3600)
    return {
        'name': name,
        'status': status,
        'detail': f'EPS brief cache refreshed {age_str}',
        'last_ok': _iso_ph(mt),
    }


def _svc_personal_crm() -> dict:
    log = _latest_match(TMP_ROOT, 'personal-crm-cleanup.log') or \
          _latest_match(PERSONAL_TMP, 'personal_crm_cleanup*.log')
    if log is None:
        return {
            'name': 'Google Sheets (Personal CRM)', 'status': 'unknown',
            'detail': 'No cleanup log found', 'last_ok': None,
        }
    mt = _mtime(log)
    status, age_str = _age_status(mt, 24 * 3600, 72 * 3600)
    return {
        'name': 'Google Sheets (Personal CRM)',
        'status': status,
        'detail': f'CRM cleanup last ran {age_str}',
        'last_ok': _iso_ph(mt) if mt else None,
    }


def _svc_fb_groups() -> dict:
    path = _latest_match(PERSONAL_TMP, 'fb_prospects_inbox*')
    if path is None:
        return {
            'name': 'Google Sheets (FB Groups)', 'status': 'unknown',
            'detail': 'No FB prospects inbox file', 'last_ok': None,
        }
    mt = _mtime(path)
    status, age_str = _age_status(mt, 24 * 3600, 72 * 3600)
    return {
        'name': 'Google Sheets (FB Groups)',
        'status': status,
        'detail': f'FB prospects inbox updated {age_str}',
        'last_ok': _iso_ph(mt) if mt else None,
    }


def _svc_anthropic_coach() -> dict:
    """
    Coach cache is in-memory only in routes_command.py. Fall back to any
    on-disk hint (brief cache is proxy for Anthropic connectivity since
    briefs call Claude). Personal brief cache is the best signal.
    """
    path = BRIEF_CACHE_DIR / 'personal.json'
    mt = _mtime(path)
    if mt is None:
        return {
            'name': 'Anthropic (Coach)', 'status': 'unknown',
            'detail': 'No brief cache yet', 'last_ok': None,
        }
    status, age_str = _age_status(mt, 30 * 60, 6 * 3600)
    return {
        'name': 'Anthropic (Coach)',
        'status': status,
        'detail': f'Last Claude-backed brief {age_str}',
        'last_ok': _iso_ph(mt),
    }


def _svc_content_buffer() -> dict:
    if not CONTENT_BUFFER.exists():
        return {
            'name': 'Content buffer', 'status': 'unknown',
            'detail': 'content-buffer.json missing', 'last_ok': None,
        }
    try:
        data = json.loads(CONTENT_BUFFER.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return {
            'name': 'Content buffer', 'status': 'red',
            'detail': f'Unreadable: {e}', 'last_ok': None,
        }
    scripts = len(data.get('scripts_ready') or [])
    recs = len(data.get('recordings') or [])
    status = 'green' if (scripts > 0 or recs > 0) else 'yellow'
    mt = _mtime(CONTENT_BUFFER)
    return {
        'name': 'Content buffer',
        'status': status,
        'detail': f'{scripts} scripts, {recs} recordings',
        'last_ok': _iso_ph(mt) if mt else None,
    }


def _svc_outcome_log() -> dict:
    if not OUTCOME_LOG.exists():
        return {
            'name': 'Outcome log', 'status': 'red',
            'detail': 'outcome_log.jsonl missing', 'last_ok': None,
        }
    today = now_ph().date().isoformat()
    today_count = 0
    last_ts = None
    try:
        with open(OUTCOME_LOG, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = row.get('ts') or row.get('timestamp') or ''
                if isinstance(ts, str) and ts.startswith(today):
                    today_count += 1
                if isinstance(ts, str):
                    last_ts = ts  # last line wins (file is append-only)
    except OSError as e:
        return {
            'name': 'Outcome log', 'status': 'red',
            'detail': f'Read error: {e}', 'last_ok': None,
        }

    mt = _mtime(OUTCOME_LOG)
    age_str = _humanize_age(datetime.now().timestamp() - mt) if mt else 'unknown'
    status = 'green' if today_count > 0 else 'yellow'
    detail = f'{today_count} entries today, last entry {age_str}'
    return {
        'name': 'Outcome log',
        'status': status,
        'detail': detail,
        'last_ok': last_ts if last_ts else (_iso_ph(mt) if mt else None),
    }


# ============================================================
# Routes
# ============================================================

@systems_bp.route('/api/brand/systems/automations')
def list_automations():
    try:
        entries = []
        for plist_path in sorted(AUTOMATION_DIR.glob('*.plist')):
            try:
                entries.append(_build_automation_entry(plist_path))
            except Exception as e:
                traceback.print_exc()
                entries.append({
                    'label': plist_path.stem,
                    'friendly_name': _friendly_name(plist_path.stem),
                    'last_run': None,
                    'last_exit_code': None,
                    'status': 'fail',
                    'schedule': 'unknown',
                    'log_path': None,
                    'plist_path': str(plist_path),
                    'sh_path': None,
                    'error': str(e),
                })
        return jsonify({'ok': True, 'automations': entries})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@systems_bp.route('/api/brand/systems/automations/<label>/log')
def automation_log(label):
    try:
        plist_path, data = _find_plist_for_label(label)
        if plist_path is None:
            return jsonify({'ok': False, 'error': f'Unknown label: {label}'}), 404

        stdout_path = data.get('StandardOutPath') or ''
        stderr_path = data.get('StandardErrorPath') or ''

        parts = []
        if stdout_path:
            out = _tail(Path(stdout_path), 50)
            if out:
                parts.append(out)
        if stderr_path and stderr_path != stdout_path:
            err = _tail(Path(stderr_path), 50)
            if err:
                parts.append('--- stderr ---\n' + err)

        combined = '\n'.join(parts)
        # Cap to last 50 lines overall
        lines = combined.splitlines()
        log_text = '\n'.join(lines[-50:])
        return jsonify({'ok': True, 'label': label, 'log': log_text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@systems_bp.route('/api/brand/systems/automations/<label>/run', methods=['POST'])
def run_automation(label):
    try:
        sh_path = _label_to_sh(label)
        if not sh_path.exists():
            return jsonify({
                'ok': False,
                'error': f'No shell script found for label {label} (expected {sh_path.name})',
            }), 400

        proc = subprocess.Popen(
            ['/bin/bash', str(sh_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            cwd=str(BASE_DIR),
            start_new_session=True,
        )
        return jsonify({'ok': True, 'message': 'Triggered', 'pid': proc.pid})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@systems_bp.route('/api/brand/systems/services')
def services():
    try:
        svcs = [
            _svc_eps_cache('Pipedrive'),
            _svc_eps_cache('ServiceM8'),
            _svc_personal_crm(),
            _svc_fb_groups(),
            _svc_anthropic_coach(),
            _svc_content_buffer(),
            _svc_outcome_log(),
        ]
        return jsonify({'ok': True, 'services': svcs})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500
