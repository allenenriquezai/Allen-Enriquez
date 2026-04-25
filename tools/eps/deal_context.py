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


def is_rescheduled(act, today_str):
    """Return True if activity shows signs of being rescheduled (bumped from an earlier date)."""
    add_date = (act.get('add_time') or '')[:10]
    due_date = act.get('due_date') or ''
    update_date = (act.get('update_time') or '')[:10]
    if not add_date or not due_date or not update_date:
        return False
    # Was modified after creation AND due date is more than 14 days after it was created
    try:
        gap = (datetime.strptime(due_date, '%Y-%m-%d') - datetime.strptime(add_date, '%Y-%m-%d')).days
    except ValueError:
        return False
    return update_date > add_date and gap > 14


def classify(item, person_activities, deal_note, today_str):
    """Classify a flagged deal based on person-level context."""
    deal_id = item['deal_id']
    today = datetime.strptime(today_str, '%Y-%m-%d')
    seven_days_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')

    # 1. Check for scheduled (future, undone) activity on ANY deal
    for act in person_activities:
        if not act.get('done') and act.get('due_date', '') >= today_str:
            deal_title = act.get('deal_title') or f"deal {act.get('deal_id', '?')}"
            subject = act.get('subject') or act.get('type', 'Activity')
            rescheduled = is_rescheduled(act, today_str)
            tag = 'RESCHEDULED' if rescheduled else 'HAS_NEXT_STEP'
            if act.get('deal_id') == deal_id:
                return tag, f'{subject} on {act["due_date"]} (this deal)'
            return tag, f'{subject} on {act["due_date"]} — {deal_title}'

    # 2. Check for recent activity on a DIFFERENT deal
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

    # 3. Only fetch note when classification is still uncertain (no next step, no recent activity)
    # Note is passed in already — caller decides whether to fetch it (tiered fetch)
    if deal_note:
        content = deal_note.get('content') or ''
        content_clean = re.sub(r'<[^>]+>', ' ', content).lower().strip()
        for kw in WAITING_KEYWORDS:
            if kw in content_clean:
                snippet = content_clean[:80].strip()
                return 'WAITING_ON_CLIENT', f'Note: {snippet}'

    # 4. Default
    return 'NEEDS_ATTENTION', 'No recent contact across any deal'


def enrich_with_person_context(action_items, *, api_key, domain, today_str):
    """Enrich flagged action items with person-level context classification.

    Mutates each item in-place, adding 'context_tag' and 'context_detail'.
    Skips overdue_activity items (those are activity-level, not deal-level).

    Tiered fetch: person activities fetched for all deals, but notes only fetched
    for deals that can't be classified from activity data alone (NEEDS_ATTENTION candidates).
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

        # Tiered note fetch: only pull note if person activities don't resolve classification
        # (skips ~70% of API calls for HAS_NEXT_STEP / ACTIVE_ELSEWHERE / RESCHEDULED deals)
        person_acts = person_cache[person_id]
        note = None
        needs_note = True
        for act in person_acts:
            if not act.get('done') and act.get('due_date', '') >= today_str:
                needs_note = False
                break
        if needs_note:
            today = __import__('datetime').datetime.strptime(today_str, '%Y-%m-%d')
            seven_days_ago = (today - __import__('datetime').timedelta(days=7)).strftime('%Y-%m-%d')
            for act in person_acts:
                act_date = act.get('due_date') or (act.get('add_time', '')[:10] if act.get('add_time') else '')
                if act_date >= seven_days_ago and act.get('deal_id') != deal_id:
                    needs_note = False
                    break

        if needs_note and deal_id not in note_cache:
            note_cache[deal_id] = fetch_deal_latest_note(deal_id, api_key=api_key, domain=domain)

        note = note_cache.get(deal_id)
        tag, detail = classify(item, person_acts, note, today_str)
        item['context_tag'] = tag
        item['context_detail'] = detail

    tags = {}
    for item in action_items:
        t = item.get('context_tag')
        if t:
            tags[t] = tags.get(t, 0) + 1
    if tags:
        print(f"  Context: {', '.join(f'{v} {k}' for k, v in tags.items())}")
