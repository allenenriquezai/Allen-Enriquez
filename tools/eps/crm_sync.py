"""
crm_sync.py — Pipedrive ↔ ServiceM8 reconciliation.

EOD sweep that checks active deals against SM8 jobs and flags/fixes mismatches.
Auto-fixes safe fields (address, contact, notes). Flags status mismatches.

Usage:
    python3 tools/crm_sync.py                    # full sync, auto-fix safe items
    python3 tools/crm_sync.py --dry-run           # show what would change, no writes
    python3 tools/crm_sync.py --print             # human-readable summary
    python3 tools/crm_sync.py --deal-id 1234      # sync a specific deal

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN
    SM8_API_KEY_CLEAN, SM8_API_KEY_PAINT
"""

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import requests

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'crm_sync.json'
DB_FILE = TMP_DIR / 'crm_cache.db'

SM8_BASE_URL = "https://api.servicem8.com/api_1.0"
API_DELAY = 0.25
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 3, 8]  # seconds between retries

# SM8 Job # custom field key in Pipedrive
SM8_JOB_FIELD_KEY = "052a8b8271d035ca4780f8ae06cd7b5370df544c"

# Address custom field key in Pipedrive deals
ADDRESS_FIELD_KEY = "3f2f68c9d737558d5f02bbbe384e4bfab75bdf39"

# Pipeline → SM8 API key mapping
PIPELINE_SM8_MAP = {
    1: 'SM8_API_KEY_CLEAN',   # EPS Clean
    2: 'SM8_API_KEY_PAINT',   # EPS Paint
}

# Stages where sync matters (deals past NEW)
SYNC_STAGES = {
    # EPS Clean
    3: 'SITE VISIT', 24: 'QUOTE IN PROGRESS', 4: 'QUOTE SENT',
    18: 'NEGOTIATION / FOLLOW UP', 5: 'LATE FOLLOW UP', 47: 'DEPOSIT PROCESS',
    # EPS Paint
    10: 'SITE VISIT', 27: 'QUOTE IN PROGRESS', 11: 'QUOTE SENT',
    17: 'NEGOTIATION / FOLLOW UP', 12: 'LATE FOLLOW UP', 48: 'DEPOSIT PROCESS',
}


# --- Env ---

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


ENV = load_env()
PIPEDRIVE_API_KEY = ENV.get('PIPEDRIVE_API_KEY', '')
PIPEDRIVE_DOMAIN = ENV.get('PIPEDRIVE_COMPANY_DOMAIN', '')
SM8_KEYS = {
    1: ENV.get('SM8_API_KEY_CLEAN', ''),
    2: ENV.get('SM8_API_KEY_PAINT', ''),
}


# --- SQLite Cache ---

def init_db():
    """Create cache tables if they don't exist."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS deals (
            deal_id INTEGER PRIMARY KEY,
            title TEXT,
            stage_id INTEGER,
            stage_name TEXT,
            pipeline_id INTEGER,
            sm8_number TEXT,
            sm8_status TEXT,
            address TEXT,
            person_name TEXT,
            person_phone TEXT,
            person_email TEXT,
            deal_value REAL,
            last_synced TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            source TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS recurring_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            job_number TEXT UNIQUE,
            visit_date TEXT,
            completion_date TEXT,
            status TEXT,
            notes TEXT,
            last_synced TEXT
        );
        CREATE TABLE IF NOT EXISTS sm8_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER,
            job_uuid TEXT,
            activity_uuid TEXT UNIQUE,
            note TEXT,
            start_date TEXT,
            end_date TEXT,
            was_scheduled INTEGER DEFAULT 0,
            staff_uuid TEXT,
            staff_name TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sm8_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER,
            job_uuid TEXT,
            file_uuid TEXT UNIQUE,
            file_name TEXT,
            file_type TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sm8_staff (
            uuid TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            pipeline_id INTEGER,
            last_fetched TEXT
        );
    """)
    conn.commit()

    # Migration: add posted_to_pd column if missing
    try:
        conn.execute("SELECT posted_to_pd FROM sm8_activities LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE sm8_activities ADD COLUMN posted_to_pd INTEGER DEFAULT 0")
        conn.commit()

    return conn


def db_get_previous(conn, deal_id):
    """Get previous cached state for a deal."""
    row = conn.execute(
        "SELECT sm8_status, address, stage_id FROM deals WHERE deal_id = ?",
        (deal_id,)
    ).fetchone()
    if row:
        return {'sm8_status': row[0], 'address': row[1], 'stage_id': row[2]}
    return None


def db_save_deal(conn, deal, sm8_job=None):
    """Upsert deal + SM8 state into cache."""
    did = deal['id']
    stage_id = deal.get('stage_id')
    stage_name = SYNC_STAGES.get(stage_id, '')
    pipeline_id = deal.get('pipeline_id')
    sm8_number = get_deal_sm8_job_number(deal)
    address = get_deal_address(deal)
    value = deal.get('value') or 0

    person = deal.get('person_id')
    person_name = person.get('name', '') if isinstance(person, dict) else ''

    sm8_status = ''
    if sm8_job:
        sm8_status = sm8_job.get('status', '').lower()
        sm8_addr = get_sm8_address(sm8_job)
        if sm8_addr:
            address = sm8_addr

    conn.execute("""
        INSERT INTO deals (deal_id, title, stage_id, stage_name, pipeline_id,
                           sm8_number, sm8_status, address, person_name,
                           person_phone, person_email, deal_value, last_synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(deal_id) DO UPDATE SET
            title=excluded.title, stage_id=excluded.stage_id,
            stage_name=excluded.stage_name, pipeline_id=excluded.pipeline_id,
            sm8_number=excluded.sm8_number, sm8_status=excluded.sm8_status,
            address=excluded.address, person_name=excluded.person_name,
            deal_value=excluded.deal_value, last_synced=excluded.last_synced
    """, (did, deal.get('title', ''), stage_id, stage_name, pipeline_id,
          sm8_number, sm8_status, address, person_name,
          '', '', value, datetime.now().strftime('%Y-%m-%d %H:%M')))


def db_log_change(conn, deal_id, field, old_val, new_val, source):
    """Log a state change to sync_log."""
    conn.execute(
        "INSERT INTO sync_log (deal_id, field, old_value, new_value, source, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (deal_id, field, old_val or '', new_val or '', source,
         datetime.now().strftime('%Y-%m-%d %H:%M'))
    )


# Recurring client → SM8 company UUID mapping (EPS Clean)
RECURRING_CLIENTS = {
    50: {'name': 'Oonagh Mitchell', 'company_uuid': 'b24aa9f2-f9ec-428d-8870-2354d875fe7b'},
    51: {'name': 'Miles Stuart', 'company_uuid': '3dc4b4ba-ba47-4976-ae0e-23b2e4938f3b'},
    52: {'name': 'Nick & Viviann Carrigan', 'company_uuid': '388a8b83-1d02-449e-af3b-23bf8018c27b'},
    53: {'name': 'Ian McRae', 'company_uuid': '1195aef4-fe82-4b15-9445-239352de1d0b'},
    54: {'name': 'Studio Pilates Coorparoo', 'company_uuid': 'a1cb1353-04b2-406b-87e1-210ff8009b0b'},
    58: {'name': 'Caitlin McLeod', 'company_uuid': '3747e1a9-0306-4927-bac2-23dd8c85ddcb'},
    61: {'name': 'Dora Telecican', 'company_uuid': 'cb32a948-6e83-4a52-b603-23d34e12ef5b'},
    63: {'name': 'Great Australia Bush Camp', 'company_uuid': None},  # TODO: find UUID
}


def sync_recurring_visits(db, sm8_key, dry_run=False, print_mode=False):
    """Fetch recent SM8 jobs for recurring clients and store in DB."""
    if not sm8_key:
        return 0

    total_stored = 0
    for project_id, client in RECURRING_CLIENTS.items():
        uuid = client.get('company_uuid')
        if not uuid:
            continue

        try:
            jobs = sm8_get("/job.json", sm8_key,
                           params={"$filter": f"company_uuid eq '{uuid}'",
                                   "$orderby": "date desc"})
        except Exception as e:
            print(f"  SM8 recurring lookup failed for {client['name']}: {e}", file=sys.stderr)
            continue

        if print_mode and jobs:
            print(f"\n  {client['name']} — {len(jobs)} SM8 jobs")

        # Store last 10 jobs
        for j in jobs[:10]:
            job_number = j.get('generated_job_id', '')
            visit_date = (j.get('date') or '')[:10]
            completion_date = (j.get('completion_date') or '')[:10]
            if completion_date.startswith('0000'):
                completion_date = ''
            status = j.get('status', '')
            notes = j.get('job_description', '').strip()

            # Get job activities/notes for more detail
            job_uuid = j.get('uuid', '')
            if job_uuid:
                try:
                    activities = sm8_get("/jobactivity.json", sm8_key,
                                        params={"$filter": f"job_uuid eq '{job_uuid}' and active eq 1"})
                    activity_notes = [a.get('note', '').strip() for a in (activities or []) if a.get('note', '').strip()]
                    if activity_notes:
                        notes = notes + ' | ' + ' | '.join(activity_notes[:3]) if notes else ' | '.join(activity_notes[:3])
                except Exception:
                    pass

            if dry_run:
                if print_mode:
                    print(f"    [DRY] #{job_number} | {visit_date} | {status} | {notes[:60]}")
                continue

            db.execute("""
                INSERT INTO recurring_visits (project_id, client_name, job_number, visit_date,
                                              completion_date, status, notes, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_number) DO UPDATE SET
                    status=excluded.status, completion_date=excluded.completion_date,
                    notes=excluded.notes, last_synced=excluded.last_synced
            """, (project_id, client['name'], job_number, visit_date,
                  completion_date, status, notes[:500],
                  datetime.now().strftime('%Y-%m-%d %H:%M')))
            total_stored += 1

            if print_mode:
                print(f"    #{job_number} | {visit_date} | {status} | {notes[:60]}")

        time.sleep(API_DELAY)

    return total_stored


SM8_STATUS_LABELS = {
    'quote': 'Quote',
    'work order': 'Work Order',
    'in progress': 'In Progress',
    'completed': 'Completed',
    'unsuccessful': 'Unsuccessful',
}


import re as _re


def _normalize_note(content):
    text = (content or '').lower().strip()
    for prefix in ('[sm8 sync] ', '[sm8 update] ', '[sm8] '):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return _re.sub(r'\s+', ' ', text)


def _already_posted(new_content, existing_notes):
    a = _normalize_note(new_content)
    if not a:
        return False
    for n in existing_notes:
        b = _normalize_note(n.get('content', ''))
        if a == b or a in b or b in a:
            return True
    return False


def post_sm8_status_note(deal_id, old_status, new_status, sm8_number, dry_run=False, existing_notes=None):
    """Post a note to Pipedrive when SM8 job status changes."""
    old_label = SM8_STATUS_LABELS.get(old_status, old_status)
    new_label = SM8_STATUS_LABELS.get(new_status, new_status)
    content = f"[SM8 Update] Job #{sm8_number}: {old_label} → {new_label}"

    if dry_run:
        print(f"    [DRY RUN] Would post note: {content}")
        return
    if existing_notes and _already_posted(content, existing_notes):
        return
    result = pd_post('/notes', {
        'content': content,
        'deal_id': deal_id,
        'pinned_to_deal_flag': 0,
    })
    if result:
        print(f"    Posted SM8 status note: {content}")


# --- Retry wrapper ---

def _retry_request(fn, label):
    """Retry a request function with exponential backoff on transient errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                print(f"  {label} → 429 rate limit, retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  {label} → {e.code}", file=sys.stderr)
            return None
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            print(f"  {label} → {e}, retry {attempt+1}/{MAX_RETRIES} in {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  {label} → failed after {MAX_RETRIES} retries", file=sys.stderr)
    return None


# --- Pipedrive API (urllib, matching crm_monitor.py) ---

def pd_get(path, params=None):
    params = params or {}
    params['api_token'] = PIPEDRIVE_API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1{path}?{qs}"

    def _do():
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())

    data = _retry_request(_do, f"PD GET {path}")
    if not data or not data.get('success'):
        return None
    return data


def pd_put(path, payload):
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1{path}?api_token={PIPEDRIVE_API_KEY}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PUT")

    def _do():
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    return _retry_request(_do, f"PD PUT {path}")


def pd_post(path, payload):
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1{path}?api_token={PIPEDRIVE_API_KEY}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    def _do():
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    return _retry_request(_do, f"PD POST {path}")


def pd_get_deal_notes(deal_id):
    url = (f"https://{PIPEDRIVE_DOMAIN}/api/v1/notes"
           f"?deal_id={deal_id}&limit=100&api_token={PIPEDRIVE_API_KEY}")

    def _do():
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get('data') or []

    return _retry_request(_do, f"PD GET notes/{deal_id}") or []


def pd_paginate(path, params=None):
    params = params or {}
    params['limit'] = 100
    start = 0
    all_items = []
    while True:
        params['start'] = start
        data = pd_get(path, params)
        if not data:
            break
        items = data.get('data') or []
        all_items.extend(items)
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination.get('next_start', start + 100)
        time.sleep(API_DELAY)
    return all_items


# --- SM8 API (requests, matching push_sm8_job.py) ---

def sm8_get(path, api_key, params=None):
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(f"{SM8_BASE_URL}{path}", headers=headers, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            print(f"  SM8 GET {path} → {e}, retry {attempt+1}/{MAX_RETRIES} in {wait}s", file=sys.stderr)
            time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                time.sleep(wait)
                continue
            raise
    raise ConnectionError(f"SM8 GET {path} failed after {MAX_RETRIES} retries")


def sm8_find_job(job_number, api_key):
    """Look up SM8 job by generated_job_id (e.g. 'EPS-6383')."""
    try:
        jobs = sm8_get("/job.json", api_key,
                       params={"$filter": f"generated_job_id eq '{job_number}'"})
        if jobs:
            return jobs[0]
    except Exception as e:
        print(f"  SM8 lookup '{job_number}' failed: {e}", file=sys.stderr)
    return None


def sm8_find_job_by_address(address, api_key):
    """Fallback: search SM8 jobs by address when Pipedrive has no SM8 job # linked.

    Searches job_address field. Returns the most recent matching job or None.
    Only matches active jobs (status != 'Unsuccessful').
    """
    if not address or len(address.strip()) < 5:
        return None

    norm = normalize_address(address)

    # Reject addresses that are too generic (just suburb/city/state — no street)
    # Must contain a digit (street number) or a street-type word to be specific enough
    import re
    has_street_number = bool(re.search(r'\d', norm))
    street_words = ('st', 'street', 'rd', 'road', 'ave', 'avenue', 'dr', 'drive',
                    'cres', 'crescent', 'ct', 'court', 'pl', 'place', 'way',
                    'parade', 'tce', 'terrace', 'blvd', 'lane', 'ln', 'circuit')
    has_street_word = any(w in norm.split() for w in street_words)
    if not has_street_number and not has_street_word:
        return None

    try:
        # Fetch recent jobs (last 200, sorted by date desc)
        jobs = sm8_get("/job.json", api_key,
                       params={"$orderby": "date desc", "$top": "200"})
        if not jobs:
            return None

        best = None
        for job in jobs:
            if job.get('status', '').lower() == 'unsuccessful':
                continue
            sm8_addr = normalize_address(get_sm8_address(job))
            if not sm8_addr:
                continue
            # Match: exact match, or one contains the other (for partial addresses)
            # Both must be specific enough (the norm check above covers Pipedrive side;
            # SM8 side must also have a digit to avoid "Brisbane QLD" matching everything)
            if not re.search(r'\d', sm8_addr):
                continue
            if sm8_addr == norm or norm in sm8_addr or sm8_addr in norm:
                best = job
                break  # First match = most recent (sorted by date desc)

        if best:
            print(f"    SM8 fallback match by address: {best.get('generated_job_id', '?')} "
                  f"({get_sm8_address(best)})")
        return best
    except Exception as e:
        print(f"  SM8 address fallback failed: {e}", file=sys.stderr)
        return None


def link_sm8_to_pipedrive(deal_id, sm8_job_number, dry_run=False):
    """Write SM8 job # back to Pipedrive deal custom field."""
    value = f"#{sm8_job_number}"
    if dry_run:
        print(f"    [DRY RUN] Would link SM8 #{sm8_job_number} → Pipedrive deal {deal_id}")
        return True
    result = pd_put(f'/deals/{deal_id}', {SM8_JOB_FIELD_KEY: value})
    if result:
        print(f"    Linked SM8 #{sm8_job_number} → Pipedrive deal {deal_id}")
        return True
    print(f"    FAILED to link SM8 #{sm8_job_number} → deal {deal_id}", file=sys.stderr)
    return False


def sm8_get_job_notes(job_uuid, api_key):
    """Get notes/activities for an SM8 job."""
    try:
        return sm8_get("/jobactivity.json", api_key,
                       params={"$filter": f"job_uuid eq '{job_uuid}' and active eq 1"})
    except Exception:
        return []


def sm8_get_job_contacts(job_uuid, api_key):
    """Get contact info from SM8 job."""
    try:
        contacts = sm8_get("/jobcontact.json", api_key,
                           params={"$filter": f"job_uuid eq '{job_uuid}' and active eq 1"})
        return contacts
    except Exception:
        return []


# --- SM8 Staff + Files ---

_staff_cache = {}  # {pipeline_id: {uuid: "First Last"}}
_files_endpoint = None  # None = untested, str = working endpoint, False = unavailable


def sm8_cache_staff(api_key, pipeline_id, db):
    """Fetch /staff.json once per pipeline per run. Returns {uuid: 'First Last'}."""
    if pipeline_id in _staff_cache:
        return _staff_cache[pipeline_id]

    staff_map = {}
    try:
        staff_list = sm8_get("/staff.json", api_key)
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        for s in (staff_list or []):
            uid = s.get('uuid', '')
            first = s.get('first', '')
            last = s.get('last', '')
            name = f"{first} {last}".strip()
            if uid and name:
                staff_map[uid] = name
                db.execute("""
                    INSERT INTO sm8_staff (uuid, first_name, last_name, pipeline_id, last_fetched)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(uuid) DO UPDATE SET
                        first_name=excluded.first_name, last_name=excluded.last_name,
                        last_fetched=excluded.last_fetched
                """, (uid, first, last, pipeline_id, now))
    except Exception as e:
        print(f"  SM8 staff fetch failed (pipeline {pipeline_id}): {e}", file=sys.stderr)
        # Fall back to cached staff from DB
        try:
            rows = db.execute("SELECT uuid, first_name, last_name FROM sm8_staff").fetchall()
            for r in rows:
                staff_map[r[0]] = f"{r[1]} {r[2]}".strip()
        except Exception:
            pass

    _staff_cache[pipeline_id] = staff_map
    return staff_map


def resolve_staff_name(staff_uuid, staff_map):
    """Look up staff name from cache."""
    if not staff_uuid:
        return ''
    return staff_map.get(staff_uuid, 'Unknown')


def sm8_get_job_files(job_uuid, api_key):
    """Fetch files/attachments for an SM8 job. Probes endpoint on first call."""
    global _files_endpoint
    if _files_endpoint is False:
        return []

    endpoints = ['/attachment.json', '/jobfile.json'] if _files_endpoint is None else [_files_endpoint]
    headers = {"X-API-Key": api_key, "Accept": "application/json"}

    for ep in endpoints:
        try:
            # Use requests directly (not sm8_get) so we can catch 400/404 gracefully
            r = requests.get(
                f"{SM8_BASE_URL}{ep}",
                headers=headers,
                params={"$filter": f"job_uuid eq '{job_uuid}' and active eq 1"},
                timeout=15,
            )
            if r.status_code in (400, 404):
                continue
            r.raise_for_status()
            _files_endpoint = ep
            return r.json() or []
        except Exception:
            continue

    # No endpoint worked
    _files_endpoint = False
    print("  SM8 file endpoint not available — photos will not be synced", file=sys.stderr)
    return []


def _classify_activity(act):
    """Derive a human-readable activity type from SM8 jobactivity fields."""
    if act.get('activity_was_scheduled'):
        return 'Booking'
    if act.get('activity_was_recorded'):
        travel = int(act.get('travel_time_in_seconds', 0) or 0)
        if travel > 0:
            return 'Job Check Out'
        return 'Check In'
    return 'Activity'


def _format_activity_note(act):
    """Build a useful note from SM8 activity fields."""
    parts = []
    # Travel + job time from recorded activities
    travel_s = int(act.get('travel_time_in_seconds', 0) or 0)
    if travel_s > 0:
        travel_m = travel_s // 60
        parts.append(f"Travel: {travel_m} min")
    start = act.get('start_date', '')
    end = act.get('end_date', '')
    if start and end and start[:10] == end[:10]:
        parts.append(f"On site: {start[11:16]} - {end[11:16]}")
    distance_m = int(act.get('travel_distance_in_meters', 0) or 0)
    if distance_m > 0:
        parts.append(f"Distance: {distance_m / 1000:.1f} km")
    # Fall back to note field if present
    note = (act.get('note', '') or '').strip()
    if note:
        parts.append(note[:500])
    return ' | '.join(parts) if parts else ''


def cache_sm8_activities(db, deal_id, job_uuid, activities, staff_map, dry_run=False):
    """Store SM8 job activities into SQLite cache."""
    if dry_run:
        return
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for act in (activities or [])[:20]:
        act_uuid = act.get('uuid', '')
        if not act_uuid:
            continue
        staff_name = resolve_staff_name(act.get('staff_uuid', ''), staff_map)
        activity_type = _classify_activity(act)
        note = _format_activity_note(act)
        db.execute("""
            INSERT INTO sm8_activities (deal_id, job_uuid, activity_uuid, note,
                                        start_date, end_date, was_scheduled,
                                        staff_uuid, staff_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(activity_uuid) DO UPDATE SET
                note=excluded.note, start_date=excluded.start_date,
                end_date=excluded.end_date, was_scheduled=excluded.was_scheduled,
                staff_name=excluded.staff_name, created_at=excluded.created_at
        """, (deal_id, job_uuid, act_uuid,
              f"[{activity_type}] {note}".strip(),
              act.get('start_date', ''), act.get('end_date', ''),
              1 if act.get('activity_was_scheduled') else 0,
              act.get('staff_uuid', ''), staff_name, now))


def cache_sm8_files(db, deal_id, job_uuid, files, dry_run=False):
    """Store SM8 job files/attachments into SQLite cache."""
    if dry_run:
        return
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for f in (files or [])[:30]:
        file_uuid = f.get('uuid', '')
        if not file_uuid:
            continue
        db.execute("""
            INSERT INTO sm8_files (deal_id, job_uuid, file_uuid, file_name, file_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_uuid) DO UPDATE SET
                file_name=excluded.file_name, file_type=excluded.file_type,
                created_at=excluded.created_at
        """, (deal_id, job_uuid, file_uuid,
              f.get('file_name', '') or f.get('name', ''),
              f.get('content_type', '') or f.get('file_type', ''),
              now))


# --- Pipedrive Projects API ---

def api_get_projects():
    """Fetch all open Pipedrive projects."""
    data = pd_get('/projects', {'status': 'open', 'limit': 500})
    if data and data.get('data'):
        return data['data']
    return []


# --- Comparison Logic ---

def normalize_address(addr):
    """Normalize address for comparison."""
    if not addr:
        return ""
    return addr.lower().strip().replace(",", "").replace("  ", " ")


def get_deal_address(deal):
    """Extract address from deal (custom field or org address)."""
    # Try custom address field first
    addr = deal.get(ADDRESS_FIELD_KEY, '')
    if addr:
        return addr

    # Try org address
    org = deal.get('org_id')
    if isinstance(org, dict):
        return org.get('address', '') or ''
    return ''


def get_sm8_address(job):
    """Extract address from SM8 job."""
    parts = []
    for field in ['job_address', 'job_city', 'job_state', 'job_postcode']:
        val = job.get(field, '')
        if val:
            parts.append(val)
    return ', '.join(parts) if parts else ''


def get_deal_sm8_job_number(deal):
    """Get SM8 Job # from Pipedrive deal custom field."""
    val = (deal.get(SM8_JOB_FIELD_KEY) or '').strip()
    # Strip leading '#' — Pipedrive stores '#EPS-6343' but SM8 uses 'EPS-6343'
    return val.lstrip('#')


def compare_deal_sm8(deal, sm8_job):
    """Compare a Pipedrive deal with its SM8 job. Returns list of diffs."""
    diffs = []

    # Address comparison
    pd_addr = normalize_address(get_deal_address(deal))
    sm8_addr = normalize_address(get_sm8_address(sm8_job))

    if pd_addr and sm8_addr and pd_addr != sm8_addr:
        diffs.append({
            'field': 'address',
            'action': 'auto_fix',
            'pipedrive': get_deal_address(deal),
            'sm8': get_sm8_address(sm8_job),
            'source_of_truth': 'sm8',
        })
    elif not pd_addr and sm8_addr:
        diffs.append({
            'field': 'address',
            'action': 'auto_fix',
            'pipedrive': '(empty)',
            'sm8': get_sm8_address(sm8_job),
            'source_of_truth': 'sm8',
        })

    # Status alignment
    sm8_status = sm8_job.get('status', '').lower()
    stage_id = deal.get('stage_id')
    stage_name = SYNC_STAGES.get(stage_id, 'UNKNOWN')

    # Flag: deal in DEPOSIT but SM8 shows Quote/Work Order
    if stage_id in (47, 48) and sm8_status in ('quote', 'work order'):
        diffs.append({
            'field': 'status',
            'action': 'flag',
            'pipedrive': f'{stage_name} (stage {stage_id})',
            'sm8': sm8_status,
            'note': 'Deal in DEPOSIT but SM8 job not progressed',
        })

    # Flag: SM8 shows completed but deal still open
    if sm8_status == 'completed' and stage_id not in (47, 48):
        diffs.append({
            'field': 'status',
            'action': 'flag',
            'pipedrive': f'{stage_name} (stage {stage_id})',
            'sm8': 'completed',
            'note': 'SM8 job completed but Pipedrive deal still in earlier stage',
        })

    return diffs


# --- Sync Actions ---

def sync_address(deal_id, sm8_address, dry_run=False):
    """Update Pipedrive deal address from SM8."""
    if dry_run:
        print(f"    [DRY RUN] Would update deal {deal_id} address → {sm8_address}")
        return True
    result = pd_put(f'/deals/{deal_id}', {ADDRESS_FIELD_KEY: sm8_address})
    if result:
        print(f"    Updated address → {sm8_address}")
        return True
    return False


def sync_notes(deal_id, sm8_notes, existing_pd_notes, dry_run=False):
    """Post SM8 notes to Pipedrive deal if not already there."""
    posted = 0
    for note in sm8_notes:
        note_text = note.get('note', '').strip()
        if not note_text or len(note_text) < 5:
            continue

        # Check if this note content already exists in Pipedrive
        note_lower = note_text[:100].lower()
        already_posted = any(note_lower in (n.get('content', '') or '').lower()
                            for n in existing_pd_notes)
        if already_posted:
            continue

        content = f"[SM8 Sync] {note_text}"
        if dry_run:
            print(f"    [DRY RUN] Would post note: {content[:80]}...")
            posted += 1
            continue

        result = pd_post('/notes', {
            'content': content,
            'deal_id': deal_id,
            'pinned_to_deal_flag': 0,
        })
        if result:
            posted += 1

    return posted


def sync_contact(deal, sm8_job, dry_run=False):
    """Update Pipedrive person phone/email from SM8 if blank."""
    person_id = deal.get('person_id')
    if isinstance(person_id, dict):
        person_id = person_id.get('value')
    if not person_id:
        return 0

    # Fetch person details
    person_data = pd_get(f'/persons/{person_id}')
    if not person_data or not person_data.get('data'):
        return 0
    person = person_data['data']

    updates = {}
    sm8_phone = sm8_job.get('job_contact_phone', '').strip()
    sm8_email = sm8_job.get('job_contact_email', '').strip()

    # Only update if Pipedrive field is blank
    pd_phones = person.get('phone', [])
    has_phone = any(p.get('value', '').strip() for p in pd_phones if isinstance(p, dict))
    if sm8_phone and not has_phone:
        updates['phone'] = [{'value': sm8_phone, 'primary': True, 'label': 'work'}]

    pd_emails = person.get('email', [])
    has_email = any(e.get('value', '').strip() for e in pd_emails if isinstance(e, dict))
    if sm8_email and not has_email:
        updates['email'] = [{'value': sm8_email, 'primary': True, 'label': 'work'}]

    if not updates:
        return 0

    if dry_run:
        print(f"    [DRY RUN] Would update person {person_id}: {list(updates.keys())}")
        return len(updates)

    result = pd_put(f'/persons/{person_id}', updates)
    if result:
        print(f"    Updated person {person_id}: {list(updates.keys())}")
        return len(updates)
    return 0


# --- Main Sync ---

def run_sync(deal_id=None, dry_run=False, print_mode=False):
    """Run the full sync process."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"CRM Sync — {timestamp}")
    if dry_run:
        print("*** DRY RUN ***\n")

    # Init SQLite cache
    db = init_db()

    results = {
        'timestamp': timestamp,
        'deals_checked': 0,
        'deals_with_sm8': 0,
        'deals_missing_sm8': [],
        'diffs_found': 0,
        'auto_fixed': 0,
        'flagged': 0,
        'notes_synced': 0,
        'contacts_updated': 0,
        'status_notes_posted': 0,
        'stages_moved': 0,
        'activities_posted': 0,
        'details': [],
    }

    # Fetch deals from sync-relevant stages
    if deal_id:
        data = pd_get(f'/deals/{deal_id}')
        deals = [data['data']] if data and data.get('data') else []
    else:
        deals = []
        for pipeline_id in [1, 2]:
            pipeline_deals = pd_paginate(f'/pipelines/{pipeline_id}/deals',
                                         {'status': 'open'})
            # Filter to sync-relevant stages
            for d in pipeline_deals:
                if d.get('stage_id') in SYNC_STAGES:
                    deals.append(d)
            time.sleep(API_DELAY)

    print(f"Deals to check: {len(deals)}\n")
    results['deals_checked'] = len(deals)

    for deal in deals:
        did = deal['id']
        title = deal.get('title', 'Unknown')
        stage_id = deal.get('stage_id')
        stage_name = SYNC_STAGES.get(stage_id, 'UNKNOWN')
        pipeline_id = deal.get('pipeline_id')

        sm8_job_number = get_deal_sm8_job_number(deal)

        # Get SM8 API key for this pipeline
        sm8_key = SM8_KEYS.get(pipeline_id)
        if not sm8_key:
            db_save_deal(db, deal)
            continue

        sm8_job = None

        if not sm8_job_number:
            # No SM8 job # in Pipedrive — try address-based fallback
            address = get_deal_address(deal)
            if address:
                sm8_job = sm8_find_job_by_address(address, sm8_key)

            if sm8_job:
                # Found via fallback — auto-link back to Pipedrive
                sm8_job_number = sm8_job.get('generated_job_id', '')
                if sm8_job_number:
                    link_sm8_to_pipedrive(did, sm8_job_number, dry_run)
                    db_log_change(db, did, 'sm8_number', '', sm8_job_number, 'auto_link')
                    if print_mode:
                        print(f"  🔗 #{did} {title} — auto-linked SM8 #{sm8_job_number} (address match)")
            else:
                # No match found — flag DEPOSIT and SITE VISIT stages
                if stage_id in (3, 10, 47, 48):  # SITE VISIT (3,10) + DEPOSIT (47,48)
                    results['deals_missing_sm8'].append({
                        'deal_id': did,
                        'title': title,
                        'stage': stage_name,
                    })
                    if print_mode:
                        print(f"  ⚠ #{did} {title} [{stage_name}] — NO SM8 JOB # (address fallback found nothing)")
                db_save_deal(db, deal)
                continue
        else:
            # Have job number — look up directly
            sm8_job = sm8_find_job(sm8_job_number, sm8_key)

        if not sm8_job:
            results['deals_missing_sm8'].append({
                'deal_id': did,
                'title': title,
                'stage': stage_name,
                'sm8_number': sm8_job_number,
                'error': 'SM8 job not found',
            })
            if print_mode:
                print(f"  ⚠ #{did} {title} — SM8 #{sm8_job_number} not found")
            continue

        results['deals_with_sm8'] += 1

        # Fetch existing Pipedrive notes once per deal for dedup checks
        pd_notes = pd_get_deal_notes(did) if not dry_run else []

        # Detect SM8 status changes and post note to Pipedrive
        prev = db_get_previous(db, did)
        sm8_status = sm8_job.get('status', '').lower()
        prev_status = (prev['sm8_status'] or '').lower() if prev else ''
        stage_moved = False

        deposit_stages = {1: 47, 2: 48}  # pipeline_id → DEPOSIT stage_id
        advance_from = {3, 10, 24, 27, 4, 11, 18, 17, 5, 12}  # SITE VISIT, QUOTE IN PROGRESS, QUOTE SENT, NEGOTIATION, LATE FU

        if prev and prev_status and prev_status != sm8_status:
            # Status CHANGED since last sync
            if sm8_status == 'work order' and stage_id in advance_from:
                target_stage = deposit_stages.get(pipeline_id)
                if target_stage:
                    note_text = (f"[SM8 Update] Job #{sm8_job_number}: "
                                 f"{SM8_STATUS_LABELS.get(prev_status, prev_status)} → Work Order "
                                 f"— Deal moved to DEPOSIT PROCESS")
                    if dry_run:
                        print(f"    [DRY RUN] Would move deal {did} to DEPOSIT (stage {target_stage})")
                        print(f"    [DRY RUN] Would post note: {note_text}")
                    else:
                        pd_put(f'/deals/{did}', {'stage_id': target_stage})
                        if not _already_posted(note_text, pd_notes):
                            pd_post('/notes', {
                                'content': note_text,
                                'deal_id': did,
                                'pinned_to_deal_flag': 0,
                            })
                        print(f"    Moved to DEPOSIT PROCESS + note posted")
                    db_log_change(db, did, 'stage_id', str(stage_id), str(target_stage), 'sm8_auto')
                    stage_moved = True
                    results['status_notes_posted'] += 1
                    results['stages_moved'] += 1
            elif sm8_status == 'completed' and stage_id not in (47, 48):
                # Completed but not in DEPOSIT — flag for Allen, don't auto-move
                note_text = (f"[SM8 Update] Job #{sm8_job_number}: "
                             f"{SM8_STATUS_LABELS.get(prev_status, prev_status)} → Completed "
                             f"— Review needed (Win/Close?)")
                if dry_run:
                    print(f"    [DRY RUN] Would post note: {note_text}")
                else:
                    if not _already_posted(note_text, pd_notes):
                        pd_post('/notes', {
                            'content': note_text,
                            'deal_id': did,
                            'pinned_to_deal_flag': 0,
                        })
                results['flagged'] += 1
                results['status_notes_posted'] += 1
            else:
                # Other status changes — post note only
                post_sm8_status_note(did, prev['sm8_status'], sm8_status, sm8_job_number, dry_run, existing_notes=pd_notes)
                results['status_notes_posted'] += 1

            db_log_change(db, did, 'sm8_status', prev['sm8_status'], sm8_status, 'sm8')
            if print_mode:
                old_l = SM8_STATUS_LABELS.get(prev_status, prev_status)
                new_l = SM8_STATUS_LABELS.get(sm8_status, sm8_status)
                extra = " (→ DEPOSIT)" if stage_moved else ""
                print(f"    SM8 status: {old_l} → {new_l}{extra}")

        # Baseline mismatch check — catches cases where SM8 was already
        # ahead when first cached (no transition seen) or cache was empty
        if not stage_moved:
            if sm8_status == 'work order' and stage_id in advance_from:
                target_stage = deposit_stages.get(pipeline_id)
                if target_stage:
                    note_text = (f"[SM8 Sync] Job #{sm8_job_number} is Work Order "
                                 f"— Deal moved to DEPOSIT PROCESS")
                    if dry_run:
                        print(f"    [DRY RUN] Baseline fix: would move deal {did} to DEPOSIT (stage {target_stage})")
                        print(f"    [DRY RUN] Would post note: {note_text}")
                    else:
                        pd_put(f'/deals/{did}', {'stage_id': target_stage})
                        if not _already_posted(note_text, pd_notes):
                            pd_post('/notes', {
                                'content': note_text,
                                'deal_id': did,
                                'pinned_to_deal_flag': 0,
                            })
                        print(f"    Baseline fix: moved to DEPOSIT PROCESS + note posted")
                    db_log_change(db, did, 'stage_id', str(stage_id), str(target_stage), 'sm8_baseline')
                    stage_moved = True
                    results['status_notes_posted'] += 1
                    results['stages_moved'] += 1
            elif sm8_status == 'completed' and stage_id not in (47, 48):
                note_text = (f"[SM8 Sync] Job #{sm8_job_number} is Completed "
                             f"— Review needed (Win/Close?)")
                if dry_run:
                    print(f"    [DRY RUN] Baseline flag: {note_text}")
                else:
                    if not _already_posted(note_text, pd_notes):
                        pd_post('/notes', {
                            'content': note_text,
                            'deal_id': did,
                            'pinned_to_deal_flag': 0,
                        })
                results['flagged'] += 1
                results['status_notes_posted'] += 1

        # Save current state to cache
        db_save_deal(db, deal, sm8_job)

        # Cache SM8 activities + files for ALL deals with SM8 jobs
        sm8_uuid = sm8_job.get('uuid', '')
        sm8_activities_raw = []
        if sm8_uuid:
            sm8_activities_raw = sm8_get_job_notes(sm8_uuid, sm8_key)
            staff_map = sm8_cache_staff(sm8_key, pipeline_id, db)
            cache_sm8_activities(db, did, sm8_uuid, sm8_activities_raw, staff_map, dry_run)
            sm8_files = sm8_get_job_files(sm8_uuid, sm8_key)
            cache_sm8_files(db, did, sm8_uuid, sm8_files, dry_run)
            if sm8_files and print_mode:
                print(f"    {len(sm8_files)} file(s) cached")

        # Post unposted SM8 activities as Pipedrive notes (for ALL deals with SM8)
        if sm8_uuid and not dry_run:
            unposted = db.execute(
                "SELECT id, note, start_date, staff_name, was_scheduled "
                "FROM sm8_activities WHERE deal_id = ? AND posted_to_pd = 0",
                (did,)
            ).fetchall()
            for row in unposted:
                act_id, act_note, act_start, act_staff, act_scheduled = row
                # Skip empty notes
                if not act_note or len(act_note.strip()) < 5:
                    db.execute("UPDATE sm8_activities SET posted_to_pd = 1 WHERE id = ?", (act_id,))
                    continue
                # Format the note for Pipedrive
                date_str = act_start[:10] if act_start else ''
                staff_str = f" — {act_staff}" if act_staff else ''
                content = f"{act_note}{staff_str}"
                if date_str:
                    content = f"{content} | {date_str}"
                # Post to Pipedrive (skip if already posted as near-duplicate)
                if _already_posted(content, pd_notes):
                    db.execute("UPDATE sm8_activities SET posted_to_pd = 1 WHERE id = ?", (act_id,))
                    continue
                result = pd_post('/notes', {
                    'content': content,
                    'deal_id': did,
                    'pinned_to_deal_flag': 0,
                })
                if result:
                    db.execute("UPDATE sm8_activities SET posted_to_pd = 1 WHERE id = ?", (act_id,))
                    results['notes_synced'] += 1
            db.commit()
        elif sm8_uuid and dry_run:
            unposted = db.execute(
                "SELECT note, start_date, staff_name FROM sm8_activities "
                "WHERE deal_id = ? AND posted_to_pd = 0 AND length(note) > 5",
                (did,)
            ).fetchall()
            if unposted and print_mode:
                print(f"    [DRY RUN] {len(unposted)} SM8 activities to post as notes")
                for row in unposted[:3]:
                    print(f"      {row[0][:80]}")
            results['notes_synced'] += len(unposted)

        # Compare address/status diffs
        diffs = compare_deal_sm8(deal, sm8_job)

        # Sync contact info (always, not just when diffs exist)
        contact_updates = sync_contact(deal, sm8_job, dry_run)
        results['contacts_updated'] += contact_updates

        if not diffs:
            if print_mode:
                print(f"  ✓ #{did} {title} — in sync")
            continue

        results['diffs_found'] += len(diffs)
        deal_detail = {
            'deal_id': did,
            'title': title,
            'stage': stage_name,
            'sm8_number': sm8_job_number,
            'diffs': diffs,
            'actions_taken': [],
        }

        if print_mode:
            print(f"\n  #{did} {title} [{stage_name}] — SM8 #{sm8_job_number}")

        for diff in diffs:
            if print_mode:
                marker = "→ FIX" if diff['action'] == 'auto_fix' else "⚠ FLAG"
                print(f"    {marker}: {diff['field']} — PD: {diff.get('pipedrive', '')} | SM8: {diff.get('sm8', '')}")

            if diff['action'] == 'auto_fix' and diff['field'] == 'address':
                if sync_address(did, diff['sm8'], dry_run):
                    results['auto_fixed'] += 1
                    deal_detail['actions_taken'].append(f"address updated → {diff['sm8']}")
            elif diff['action'] == 'flag':
                results['flagged'] += 1
                deal_detail['actions_taken'].append(f"FLAGGED: {diff.get('note', diff['field'])}")

        results['details'].append(deal_detail)

    # --- Projects Sync ---
    # Check Pipedrive Projects (boards 1-2) against SM8
    if not deal_id:
        print(f"\nChecking Projects (boards 1-2)...")
        projects_data = api_get_projects()
        projects_checked = 0

        for proj in projects_data:
            board_id = proj.get('board_id')
            if board_id not in (1, 2):
                continue

            # Get linked deal for SM8 job number
            linked_deals = proj.get('deal_ids', [])
            if not linked_deals:
                continue

            deal_data = pd_get(f'/deals/{linked_deals[0]}')
            if not deal_data or not deal_data.get('data'):
                continue
            deal = deal_data['data']
            pipeline_id = deal.get('pipeline_id')

            sm8_job_number = get_deal_sm8_job_number(deal)
            if not sm8_job_number:
                continue

            sm8_key = SM8_KEYS.get(pipeline_id)
            if not sm8_key:
                continue

            sm8_job = sm8_find_job(sm8_job_number, sm8_key)
            if not sm8_job:
                continue

            projects_checked += 1

            # Check SM8 status vs project phase
            sm8_status = sm8_job.get('status', '').lower()
            phase_id = proj.get('phase_id')

            # Flag: project in Booked (phase 4,9) but SM8 shows completed
            if phase_id in (4, 9) and sm8_status == 'completed':
                results['flagged'] += 1
                if print_mode:
                    print(f"  ⚠ Project '{proj.get('title', '?')}' — phase Booked but SM8 completed")
                results['details'].append({
                    'type': 'project',
                    'project_id': proj['id'],
                    'title': proj.get('title', ''),
                    'sm8_status': sm8_status,
                    'note': 'Project in Booked but SM8 job completed — move to Completed phase?',
                })

            # Flag: project in Completed (phase 1,11) but SM8 still in progress
            if phase_id in (1, 11) and sm8_status in ('work order', 'in progress'):
                results['flagged'] += 1
                if print_mode:
                    print(f"  ⚠ Project '{proj.get('title', '?')}' — phase Completed but SM8 in progress")

            # Cache SM8 activities + files for project's linked deal
            sm8_uuid = sm8_job.get('uuid', '')
            deal_id_for_cache = linked_deals[0]
            if sm8_uuid:
                staff_map = sm8_cache_staff(sm8_key, pipeline_id, db)
                proj_activities = sm8_get_job_notes(sm8_uuid, sm8_key)
                cache_sm8_activities(db, deal_id_for_cache, sm8_uuid, proj_activities, staff_map, dry_run)
                proj_files = sm8_get_job_files(sm8_uuid, sm8_key)
                cache_sm8_files(db, deal_id_for_cache, sm8_uuid, proj_files, dry_run)
                if print_mode:
                    act_count = len(proj_activities or [])
                    file_count = len(proj_files or [])
                    if act_count or file_count:
                        print(f"    Project '{proj.get('title', '?')}': {act_count} activities, {file_count} files cached")

            time.sleep(API_DELAY)

        print(f"  Projects checked: {projects_checked}")

    # --- Recurring Clients Sync ---
    if not deal_id:
        print(f"\nSyncing recurring clients...")
        sm8_clean_key = SM8_KEYS.get(1, '')
        recurring_stored = sync_recurring_visits(db, sm8_clean_key, dry_run, print_mode)
        results['recurring_visits_stored'] = recurring_stored
        print(f"  Recurring visits stored: {recurring_stored}")

    # Commit DB
    db.commit()
    db.close()

    # Save output
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2, default=str))

    # Summary
    print(f"\n{'='*50}")
    print(f"  CRM SYNC SUMMARY — {timestamp}")
    print(f"{'='*50}")
    print(f"  Deals checked:      {results['deals_checked']}")
    print(f"  With SM8 match:     {results['deals_with_sm8']}")
    print(f"  Missing SM8:        {len(results['deals_missing_sm8'])}")
    print(f"  Diffs found:        {results['diffs_found']}")
    print(f"  Auto-fixed:         {results['auto_fixed']}")
    print(f"  Flagged:            {results['flagged']}")
    print(f"  SM8 status notes:   {results['status_notes_posted']}")
    print(f"  Stages moved:       {results['stages_moved']}")
    print(f"  Activities posted:  {results['notes_synced']}")
    print(f"  Contacts updated:   {results['contacts_updated']}")
    print(f"{'='*50}")

    if results['deals_missing_sm8']:
        print(f"\n  Missing SM8 Job #:")
        for d in results['deals_missing_sm8']:
            print(f"    #{d['deal_id']} {d['title']} [{d['stage']}]")

    return results


def main():
    parser = argparse.ArgumentParser(description="CRM Sync — Pipedrive ↔ ServiceM8")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes, no writes')
    parser.add_argument('--print', action='store_true', dest='print_mode', help='Human-readable output')
    parser.add_argument('--deal-id', type=int, help='Sync a specific deal')
    args = parser.parse_args()

    if not PIPEDRIVE_API_KEY or not PIPEDRIVE_DOMAIN:
        print("ERROR: Set PIPEDRIVE_API_KEY and PIPEDRIVE_COMPANY_DOMAIN in projects/eps/.env")
        sys.exit(1)

    run_sync(
        deal_id=args.deal_id,
        dry_run=args.dry_run,
        print_mode=args.print_mode or args.dry_run,
    )


if __name__ == '__main__':
    main()
