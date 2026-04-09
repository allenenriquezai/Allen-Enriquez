"""
Deal Context — enrich flagged action items with person-level conversation history.

For each flagged deal, checks the person's activity across ALL their deals and the
deal's latest note to classify why the deal is in its current state.

Pure Python heuristics, no LLM.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

API_DELAY = 0.25

WAITING_KEYWORDS = [
    'waiting', 'pending', 'client to confirm', 'will get back',
    'awaiting', 'on hold', 'they will', 'chasing', 'no rush',
    'let us know', 'get back to us', 'thinking about it',
]


def api_get(path, params=None, *, api_key, domain):
    params = params or {}
    params['api_token'] = api_key
    qs = urllib.parse.urlencode(params)
    url = f"https://{domain}/v1{path}?{qs}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read())
        else:
            print(f"ERROR: API GET {path} returned {e.code}", file=sys.stderr)
            return None
    if not data.get('success'):
        return None
    return data


def fetch_person_activities(person_id, *, api_key, domain):
    """Fetch recent activities for a person across all their deals."""
    time.sleep(API_DELAY)
    data = api_get(f'/persons/{person_id}/activities', {'limit': 50}, api_key=api_key, domain=domain)
    if not data:
        return []
    return data.get('data') or []


def fetch_deal_latest_note(deal_id, *, api_key, domain):
    """Fetch the most recent note on a deal."""
    time.sleep(API_DELAY)
    data = api_get(f'/deals/{deal_id}/notes', {'limit': 1, 'sort': 'add_time DESC'}, api_key=api_key, domain=domain)
    if not data:
        return None
    notes = data.get('data') or []
    return notes[0] if notes else None


def classify(item, person_activities, deal_note, today_str):
    """Classify a flagged deal based on person-level context."""
    deal_id = item['deal_id']
    today = datetime.strptime(today_str, '%Y-%m-%d')
    seven_days_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')

    # 1. Check latest note for "waiting" keywords
    if deal_note:
        content = deal_note.get('content') or ''
        content_clean = re.sub(r'<[^>]+>', ' ', content).lower().strip()
        for kw in WAITING_KEYWORDS:
            if kw in content_clean:
                snippet = content_clean[:80].strip()
                return 'WAITING_ON_CLIENT', f'Note: {snippet}'

    # 2. Check for scheduled (future, undone) activity on ANY deal
    for act in person_activities:
        if not act.get('done') and act.get('due_date', '') >= today_str:
            deal_title = act.get('deal_title') or f"deal {act.get('deal_id', '?')}"
            subject = act.get('subject') or act.get('type', 'Activity')
            if act.get('deal_id') == deal_id:
                return 'HAS_NEXT_STEP', f'{subject} on {act["due_date"]} (this deal)'
            return 'HAS_NEXT_STEP', f'{subject} on {act["due_date"]} — {deal_title}'

    # 3. Check for recent activity on a DIFFERENT deal
    for act in person_activities:
        act_date = act.get('due_date') or (act.get('add_time', '')[:10] if act.get('add_time') else '')
        if not act_date:
            continue
        if act_date >= seven_days_ago and act.get('deal_id') != deal_id:
            try:
                days_ago = (today - datetime.strptime(act_date, '%Y-%m-%d')).days
            except ValueError:
                continue
            deal_title = act.get('deal_title') or f"deal {act.get('deal_id', '?')}"
            return 'ACTIVE_ELSEWHERE', f'Active {days_ago}d ago on {deal_title}'

    # 4. Default
    return 'NEEDS_ATTENTION', 'No recent contact across any deal'


def enrich_with_person_context(action_items, *, api_key, domain, today_str):
    """Enrich flagged action items with person-level context classification.

    Mutates each item in-place, adding 'context_tag' and 'context_detail'.
    Skips overdue_activity items (those are activity-level, not deal-level).
    """
    person_cache = {}  # person_id -> activities list
    note_cache = {}    # deal_id -> note dict or None

    for item in action_items:
        if item.get('type') == 'overdue_activity':
            continue

        person_id = item.get('person_id')
        deal_id = item.get('deal_id')

        if not person_id:
            item['context_tag'] = 'NEEDS_ATTENTION'
            item['context_detail'] = 'No person linked to deal'
            continue

        # Fetch person activities (cached)
        if person_id not in person_cache:
            person_cache[person_id] = fetch_person_activities(person_id, api_key=api_key, domain=domain)

        # Fetch deal note (cached)
        if deal_id not in note_cache:
            note_cache[deal_id] = fetch_deal_latest_note(deal_id, api_key=api_key, domain=domain)

        tag, detail = classify(item, person_cache[person_id], note_cache[deal_id], today_str)
        item['context_tag'] = tag
        item['context_detail'] = detail

    tags = {}
    for item in action_items:
        t = item.get('context_tag')
        if t:
            tags[t] = tags.get(t, 0) + 1
    if tags:
        print(f"  Context: {', '.join(f'{v} {k}' for k, v in tags.items())}")
