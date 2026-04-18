"""
Deal API routes — view context, mark activities done, add notes, click-to-call.
Pipedrive-backed endpoints for the EPS sales briefing dashboard.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).parent.parent))
from crm_monitor import load_env, STAGES, PIPELINES

deal_bp = Blueprint('deal', __name__)

# --- Credentials ---
_env = load_env()
API_KEY = _env.get('PIPEDRIVE_API_KEY', '')
DOMAIN = _env.get('PIPEDRIVE_COMPANY_DOMAIN', '')

# --- Simple cache: {cache_key: (timestamp, data)} ---
_cache = {}
CACHE_TTL = 60


def _cache_get(key):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _cache_set(key, data):
    _cache[key] = (time.time(), data)


# --- Pipedrive helpers ---

def api_get(path, params=None):
    params = params or {}
    params['api_token'] = API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"https://{DOMAIN}/v1{path}?{qs}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read())
        else:
            return None
    if not data.get('success'):
        return None
    return data


def api_put(path, body):
    params = {'api_token': API_KEY}
    qs = urllib.parse.urlencode(params)
    url = f"https://{DOMAIN}/v1{path}?{qs}"
    payload = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='PUT')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        else:
            return None
    if not data.get('success'):
        return None
    return data


def api_post(path, body):
    params = {'api_token': API_KEY}
    qs = urllib.parse.urlencode(params)
    url = f"https://{DOMAIN}/v1{path}?{qs}"
    payload = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        else:
            return None
    if not data.get('success'):
        return None
    return data


def strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', ' ', text).strip()


# --- Endpoints ---

@deal_bp.route('/api/deal/<int:deal_id>/context')
def deal_context(deal_id):
    if not API_KEY or not DOMAIN:
        return jsonify(ok=False, error='Pipedrive not configured'), 500

    cached = _cache_get(f'deal_{deal_id}')
    if cached:
        return jsonify(cached)

    # Fetch deal
    deal_resp = api_get(f'/deals/{deal_id}')
    if not deal_resp:
        return jsonify(ok=False, error='Deal not found'), 404

    d = deal_resp['data']
    stage_id = d.get('stage_id')
    pipeline_id = d.get('pipeline_id')
    stage_name = STAGES.get(stage_id, (str(stage_id),))[0] if stage_id else ''
    pipeline_name = PIPELINES.get(pipeline_id, str(pipeline_id)) if pipeline_id else ''

    person_id = d.get('person_id', {}).get('value') if isinstance(d.get('person_id'), dict) else d.get('person_id')
    org_name = d.get('org_name', '') or ''

    # Fetch person details
    person_name = ''
    person_phone = ''
    person_email = ''
    if person_id:
        person_resp = api_get(f'/persons/{person_id}')
        if person_resp:
            p = person_resp['data']
            person_name = p.get('name', '')
            phones = p.get('phone', [])
            if phones and isinstance(phones, list):
                person_phone = phones[0].get('value', '') if phones else ''
            emails = p.get('email', [])
            if emails and isinstance(emails, list):
                person_email = emails[0].get('value', '') if emails else ''

    deal_out = {
        'id': d.get('id'),
        'title': d.get('title', ''),
        'value': d.get('value', 0),
        'currency': d.get('currency', 'AUD'),
        'stage': stage_name,
        'pipeline': pipeline_name,
        'person_name': person_name,
        'person_phone': person_phone,
        'person_email': person_email,
        'org_name': org_name,
    }

    # Fetch activities
    act_resp = api_get(f'/deals/{deal_id}/activities', {
        'limit': '15',
        'sort': 'due_date DESC',
    })
    activities = []
    if act_resp and act_resp.get('data'):
        for a in act_resp['data']:
            activities.append({
                'type': a.get('type', ''),
                'subject': a.get('subject', ''),
                'done': bool(a.get('done')),
                'due_date': a.get('due_date', ''),
                'note': strip_html(a.get('note', '')),
            })

    # Fetch notes
    notes_resp = api_get(f'/deals/{deal_id}/notes', {
        'limit': '10',
        'sort': 'add_time DESC',
    })
    notes = []
    if notes_resp and notes_resp.get('data'):
        for n in notes_resp['data']:
            notes.append({
                'content': strip_html(n.get('content', '')),
                'add_time': n.get('add_time', ''),
                'pinned': bool(n.get('pinned_to_deal_flag')),
            })

    result = {
        'ok': True,
        'deal': deal_out,
        'activities': activities,
        'notes': notes,
    }
    _cache_set(f'deal_{deal_id}', result)
    return jsonify(result)


@deal_bp.route('/api/activity/<int:activity_id>/done', methods=['POST'])
def mark_activity_done(activity_id):
    if not API_KEY or not DOMAIN:
        return jsonify(ok=False, error='Pipedrive not configured'), 500

    resp = api_put(f'/activities/{activity_id}', {'done': 1})
    if not resp:
        return jsonify(ok=False, error='Failed to update activity'), 502

    return jsonify(ok=True)


@deal_bp.route('/api/deal/<int:deal_id>/note', methods=['POST'])
def add_deal_note(deal_id):
    if not API_KEY or not DOMAIN:
        return jsonify(ok=False, error='Pipedrive not configured'), 500

    body = request.get_json(silent=True) or {}
    content = (body.get('content') or '').strip()
    if not content:
        return jsonify(ok=False, error='Content is required'), 400

    resp = api_post('/notes', {'deal_id': deal_id, 'content': content})
    if not resp:
        return jsonify(ok=False, error='Failed to add note'), 502

    # Invalidate cache for this deal
    _cache.pop(f'deal_{deal_id}', None)

    return jsonify(ok=True, note_id=resp['data'].get('id'))


@deal_bp.route('/api/deal/<int:deal_id>/call-url')
def deal_call_url(deal_id):
    if not API_KEY or not DOMAIN:
        return jsonify(ok=False, error='Pipedrive not configured'), 500

    deal_resp = api_get(f'/deals/{deal_id}')
    if not deal_resp:
        return jsonify(ok=False, error='Deal not found'), 404

    d = deal_resp['data']
    person_id = d.get('person_id', {}).get('value') if isinstance(d.get('person_id'), dict) else d.get('person_id')

    if not person_id:
        return jsonify(ok=False, error='No contact linked to deal'), 404

    person_resp = api_get(f'/persons/{person_id}')
    if not person_resp:
        return jsonify(ok=False, error='Contact not found'), 404

    p = person_resp['data']
    phones = p.get('phone', [])
    phone = ''
    if phones and isinstance(phones, list):
        phone = phones[0].get('value', '')

    if not phone:
        return jsonify(ok=False, error='No phone number on contact'), 404

    return jsonify(ok=True, phone=phone, tel_url=f'tel:{phone}')
