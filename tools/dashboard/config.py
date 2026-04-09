"""
Centralized config — reads env vars first (cloud), falls back to .env files (local).
"""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Philippine Standard Time (UTC+8)
PH_TZ = timezone(timedelta(hours=8))


def now_ph():
    """Return current datetime in Philippine time."""
    return datetime.now(PH_TZ)


def today_ph():
    """Return today's date string (YYYY-MM-DD) in Philippine time."""
    return now_ph().strftime('%Y-%m-%d')

BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
EPS_ENV = BASE_DIR / 'projects' / 'eps' / '.env'
PERSONAL_ENV = BASE_DIR / 'projects' / 'personal' / '.env'

_loaded = False


def _load_dotenvs():
    """Load .env files into os.environ (only if not already set)."""
    global _loaded
    if _loaded:
        return
    for env_file in [EPS_ENV, PERSONAL_ENV]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
    _loaded = True


def get_anthropic_key():
    _load_dotenvs()
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not key:
        raise RuntimeError('ANTHROPIC_API_KEY not set')
    return key


def get_pipedrive_creds():
    _load_dotenvs()
    api_key = os.environ.get('PIPEDRIVE_API_KEY', '')
    domain = os.environ.get('PIPEDRIVE_COMPANY_DOMAIN', '')
    if not api_key or not domain:
        raise RuntimeError('PIPEDRIVE_API_KEY or PIPEDRIVE_COMPANY_DOMAIN not set')
    return {'api_key': api_key, 'domain': domain}


def get_dashboard_token():
    _load_dotenvs()
    return os.environ.get('DASHBOARD_TOKEN', '')


def get_eps_token_path():
    return os.environ.get(
        'GOOGLE_EPS_TOKEN_PATH',
        str(BASE_DIR / 'projects' / 'eps' / 'token_eps.pickle')
    )


def get_personal_token_path():
    return os.environ.get(
        'GOOGLE_PERSONAL_TOKEN_PATH',
        str(BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle')
    )


def get_base_dir():
    return str(BASE_DIR)
