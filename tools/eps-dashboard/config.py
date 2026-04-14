"""
EPS Dashboard config — env loading, paths, timezone.
"""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

AEST = timezone(timedelta(hours=10))
BASE_DIR = Path(__file__).parent.parent.parent  # Allen Enriquez/
EPS_ENV = BASE_DIR / 'projects' / 'eps' / '.env'

# Data paths
DEALS_DIR = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'deals'
PROJECTS_DIR = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'projects'
E1_LATEST = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'estimateone' / 'e1_latest.json'
CRM_SYNC_FILE = BASE_DIR / '.tmp' / 'crm_sync.json'
QUESTIONS_FILE = BASE_DIR / '.tmp' / 'pending_questions.json'
EOD_REPORT_FILE = BASE_DIR / '.tmp' / 'eod_report.json'
REENGAGE_CLIENTS = BASE_DIR / '.tmp' / 'reengage_clients.json'
REENGAGE_LOST = BASE_DIR / '.tmp' / 'reengage_lost.json'

_loaded = False


def _load_env():
    global _loaded
    if _loaded:
        return
    if EPS_ENV.exists():
        for line in EPS_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    _loaded = True


def get_pipedrive_creds():
    _load_env()
    api_key = os.environ.get('PIPEDRIVE_API_KEY', '')
    domain = os.environ.get('PIPEDRIVE_COMPANY_DOMAIN', '')
    if not api_key or not domain:
        raise RuntimeError('PIPEDRIVE_API_KEY or PIPEDRIVE_COMPANY_DOMAIN not set')
    return {'api_key': api_key, 'domain': domain}


def get_dashboard_token():
    _load_env()
    return os.environ.get('EPS_DASHBOARD_TOKEN', '')


def now_aest():
    return datetime.now(AEST)


def today_aest():
    return now_aest().strftime('%Y-%m-%d')
