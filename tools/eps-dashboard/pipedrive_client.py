"""
Pipedrive API client for EPS Dashboard.
Pulls live deals and projects from Pipedrive.
"""

import time
from datetime import datetime

import requests

from config import get_pipedrive_creds

API_DELAY = 0.25

# Pipeline IDs
PIPELINES = {
    1: 'EPS Clean', 2: 'EPS Paint',
    3: 'Tenders - Clean', 4: 'Tenders - Paint',
    9: 'Re-engagement',
    10: 'Win-Back',
}

# Stage ID → (name, pipeline_id)
STAGES = {
    22: ('NEW', 1), 3: ('SITE VISIT', 1), 24: ('QUOTE IN PROGRESS', 1),
    4: ('QUOTE SENT', 1), 18: ('NEGOTIATION / FOLLOW UP', 1),
    5: ('LATE FOLLOW UP', 1), 47: ('DEPOSIT PROCESS', 1),
    21: ('NEW', 2), 10: ('SITE VISIT', 2), 27: ('QUOTE IN PROGRESS', 2),
    11: ('QUOTE SENT', 2), 17: ('NEGOTIATION / FOLLOW UP', 2),
    12: ('LATE FOLLOW UP', 2), 48: ('DEPOSIT PROCESS', 2),
    31: ('QUOTE IN PROGRESS', 3), 57: ('QUOTE SENT', 3), 58: ('FOLLOW UP', 3),
    32: ('CONTACT MADE', 3), 33: ('NEGOTIATION / FOLLOW UP', 3), 34: ('LATE FOLLOW UP', 3),
    35: ('QUOTE IN PROGRESS', 4), 59: ('QUOTE SENT', 4), 60: ('FOLLOW UP', 4),
    36: ('CONTACT MADE', 4), 37: ('NEGOTIATION / FOLLOW UP', 4), 38: ('LATE FOLLOW UP', 4),
    # Re-engagement pipeline (ID: 9)
    68: ('NEW', 9), 69: ('CONTACTED', 9), 70: ('RESPONDED', 9),
    71: ('REFERRAL GIVEN', 9), 72: ('REPEAT QUOTE', 9),
    73: ('GOOGLE REVIEW', 9), 74: ('DONE', 9),
    # Win-Back pipeline (ID: 10)
    75: ('NEW', 10), 76: ('QUALIFIED', 10), 77: ('NOT WORTH IT', 10),
    78: ('CONTACTED', 10), 79: ('INTERESTED', 10),
}

# Custom field keys
SM8_JOB_FIELD = "052a8b8271d035ca4780f8ae06cd7b5370df544c"
ADDRESS_FIELD = "3f2f68c9d737558d5f02bbbe384e4bfab75bdf39"

# Project boards
PROJECT_BOARDS = {
    1: 'EPS Clean Projects', 2: 'EPS Paint Projects',
    3: 'Clean Re-engagement', 5: 'Paint Re-engagement',
}

# Phase ID → name (from eod_ops_manager.py)
PROJECT_PHASES = {
    35: 'Recurring Active', 36: 'New', 3: 'Pending Booking', 4: 'Booked',
    5: 'Fixups', 1: 'Completed', 27: 'Variations', 6: 'Final Invoice',
    37: 'New', 8: 'Pending Booking', 9: 'Booked', 10: 'Fix Ups',
    11: 'Completed', 12: 'Variations', 25: 'Final Invoice',
    26: 'Forward to Google Review',
    13: 'New / For Review', 14: 'Added to Sequence',
    15: 'Contact Made / Responded', 16: 'Google Review Done',
    17: 'Interested / Cross-sell', 28: 'Not Interested',
    29: 'New / For Review', 30: 'Added to Sequence',
    31: 'Contact Made / Responded', 32: 'Google Review Done',
    33: 'Interested / Cross-sell', 34: 'Not Interested',
}


def _api_get(path, params=None):
    """GET request to Pipedrive API with auto-retry on 429."""
    creds = get_pipedrive_creds()
    params = params or {}
    params['api_token'] = creds['api_key']
    url = f"https://{creds['domain']}/api/v1{path}"
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        time.sleep(2)
        resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _paginate(path, params=None):
    """Fetch all pages from a Pipedrive endpoint."""
    params = params or {}
    params['limit'] = 100
    start = 0
    items = []
    while True:
        params['start'] = start
        data = _api_get(path, params)
        items.extend(data.get('data') or [])
        pag = data.get('additional_data', {}).get('pagination', {})
        if not pag.get('more_items_in_collection'):
            break
        start = pag.get('next_start', start + 100)
        time.sleep(API_DELAY)
    return items


def _get_last_activity(deal):
    """Extract most recent activity date from a deal."""
    for field in ('last_activity_date', 'update_time', 'stage_change_time'):
        val = deal.get(field)
        if val:
            return val[:10]
    return None


def fetch_all_deals():
    """Fetch all open deals and assign pipeline from deal's own pipeline_id."""
    today = datetime.now().strftime('%Y-%m-%d')
    raw_deals = _paginate('/deals', {'status': 'open'})
    all_deals = []
    for d in raw_deals:
        pipeline_id = d.get('pipeline_id', 0)
        pipeline_name = PIPELINES.get(pipeline_id)
        if not pipeline_name:
            continue  # skip deals not in our 4 pipelines

        stage_id = d.get('stage_id', 0)
        stage_info = STAGES.get(stage_id)
        stage_name = stage_info[0] if stage_info else 'UNKNOWN'
        last_act = _get_last_activity(d)
        days_since = 0
        if last_act:
            try:
                days_since = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(last_act, '%Y-%m-%d')).days
            except ValueError:
                pass

        # Person info
        person = d.get('person_id') or {}
        if isinstance(person, dict):
            person_name = person.get('name', '')
            person_email = ''
            emails = person.get('email', [])
            if emails and isinstance(emails, list):
                person_email = emails[0].get('value', '') if isinstance(emails[0], dict) else ''
        else:
            person_name = ''
            person_email = ''

        # Org info
        org = d.get('org_id') or {}
        org_name = org.get('name', '') if isinstance(org, dict) else ''

        all_deals.append({
            'deal_id': d['id'],
            'title': d.get('title', ''),
            'client': person_name,
            'email': person_email,
            'org': org_name,
            'address': d.get(ADDRESS_FIELD, '') or '',
            'pipeline': pipeline_name,
            'pipeline_id': pipeline_id,
            'stage': stage_name,
            'stage_id': stage_id,
            'value': d.get('value', 0) or 0,
            'sm8_job': d.get(SM8_JOB_FIELD, '') or '',
            'last_activity': last_act or '',
            'days_since_activity': days_since,
            'currency': d.get('currency', 'AUD'),
        })
    return all_deals


def fetch_all_projects():
    """Fetch all open projects and assign board from project's own board_id."""
    today = datetime.now().strftime('%Y-%m-%d')
    raw_projects = _paginate('/projects', {'status': 'open'})
    all_projects = []
    for p in raw_projects:
        board_id = p.get('board_id', 0)
        board_name = PROJECT_BOARDS.get(board_id)
        if not board_name:
            continue  # skip projects not in our 4 boards

        last_update = (p.get('update_time') or p.get('add_time') or '')[:10]
        days_since = 0
        if last_update:
            try:
                days_since = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(last_update, '%Y-%m-%d')).days
            except ValueError:
                pass
        phase_id = p.get('phase_id', 0) or 0
        phase_name = PROJECT_PHASES.get(phase_id, '')
        all_projects.append({
            'project_id': p['id'],
            'title': p.get('title', ''),
            'board': board_name,
            'board_id': board_id,
            'phase': phase_name,
            'phase_id': phase_id,
            'status': p.get('status', ''),
            'last_update': last_update,
            'days_since_update': days_since,
            'deal_ids': p.get('deal_ids', []),
            'person_id': p.get('person_id', 0),
        })
    return all_projects


def fetch_deal_notes(deal_id):
    """Fetch notes for a specific deal, newest first."""
    data = _api_get(f'/deals/{deal_id}/notes', {'sort': 'update_time DESC'})
    notes = []
    for n in (data.get('data') or []):
        content = n.get('content', '')
        # Strip HTML tags for plain text display
        import re
        clean = re.sub(r'<[^>]+>', '', content).strip()
        notes.append({
            'content': clean,
            'add_time': (n.get('add_time') or '')[:16],
            'update_time': (n.get('update_time') or '')[:16],
            'pinned': n.get('pinned_to_deal_flag', 0) == 1,
            'user': (n.get('user', {}) or {}).get('name', ''),
        })
    return notes[:3]
