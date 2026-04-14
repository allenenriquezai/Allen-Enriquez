"""
Data loader — reads EOD JSON files and merges with live Pipedrive data.
"""

import json
import sqlite3
from pathlib import Path

from config import (
    DEALS_DIR, PROJECTS_DIR, E1_LATEST, CRM_SYNC_FILE,
    QUESTIONS_FILE, EOD_REPORT_FILE,
)

CRM_CACHE_DB = Path(__file__).parent.parent.parent / '.tmp' / 'crm_cache.db'


def _read_json(path):
    """Read a JSON file, return {} or [] on failure."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_eod_deal(deal_id):
    """Load EOD context for a single deal."""
    return _read_json(DEALS_DIR / f'{deal_id}.json')


def load_eod_project(project_id):
    """Load EOD context for a single project."""
    return _read_json(PROJECTS_DIR / f'{project_id}.json')


def _load_sm8_cache():
    """Load SM8 status cache from SQLite. Returns {deal_id: sm8_status}.

    Includes ALL deals — even those with empty sm8_status — so the dashboard
    can distinguish 'no SM8 linked' from 'deal not in cache at all'.
    """
    if not CRM_CACHE_DB.exists():
        return {}
    try:
        conn = sqlite3.connect(str(CRM_CACHE_DB))
        rows = conn.execute(
            "SELECT deal_id, sm8_status FROM deals"
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        import sys
        print(f"[data_loader] SM8 cache load failed: {e}", file=sys.stderr)
        return {}


def merge_deals_with_eod(live_deals):
    """Merge live Pipedrive deals with EOD analysis (flags, next_action) + SM8 status."""
    sm8_cache = _load_sm8_cache()
    for deal in live_deals:
        eod = load_eod_deal(deal['deal_id'])
        deal['flags'] = eod.get('flags', [])
        deal['next_action'] = eod.get('next_action', '')
        deal['max_days_before_overdue'] = eod.get('max_days_before_overdue', 0)
        deal['sm8_status'] = sm8_cache.get(deal['deal_id'], '')
    return live_deals


def merge_projects_with_eod(live_projects):
    """Merge live Pipedrive projects with EOD analysis."""
    for proj in live_projects:
        eod = load_eod_project(proj['project_id'])
        proj['flags'] = eod.get('flags', [])
        proj['next_action'] = eod.get('next_action', '')
    return live_projects


def load_questions():
    """Load pending questions from EOD ops manager."""
    data = _read_json(QUESTIONS_FILE)
    if isinstance(data, list):
        return data
    return data.get('questions', []) if isinstance(data, dict) else []


def load_tenders():
    """Load latest E1 tender data."""
    data = _read_json(E1_LATEST)
    sections = data.get('sections', {})
    return {
        'scraped_at': data.get('scraped_at', ''),
        'leads': sections.get('leads', []),
        'open_tenders': sections.get('open_tenders', []),
    }


def load_crm_sync():
    """Load latest CRM sync report."""
    return _read_json(CRM_SYNC_FILE)


def load_eod_report():
    """Load EOD report summary."""
    return _read_json(EOD_REPORT_FILE)


def get_overview_stats(deals, projects, tenders, questions):
    """Calculate overview summary stats."""
    active_deals = len(deals)
    total_value = sum(d.get('value', 0) for d in deals)
    quotes_pending = len([d for d in deals if d.get('stage') == 'QUOTE SENT'])
    tenders_open = len(tenders.get('leads', []))
    projects_active = len(projects)
    flagged = len([d for d in deals if d.get('flags')])
    flagged += len([p for p in projects if p.get('flags')])
    questions_count = len(questions)

    return {
        'active_deals': active_deals,
        'total_value': total_value,
        'quotes_pending': quotes_pending,
        'tenders_open': tenders_open,
        'projects_active': projects_active,
        'flagged': flagged,
        'questions_count': questions_count,
    }
