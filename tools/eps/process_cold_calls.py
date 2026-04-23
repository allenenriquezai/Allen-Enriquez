"""
Batch post-call processor for cold outreach leads.

After a calling session, fetches all recently called leads from the Pipedrive
filter, gets each lead's activity type + Allen's free-form note, and writes
a batch JSON for the eps-cold-calls agent to format.

Usage:
    python3 tools/process_cold_calls.py fetch                    # fetch all
    python3 tools/process_cold_calls.py fetch --connected-only   # only leads Allen spoke to
    python3 tools/process_cold_calls.py fetch --dry-run --limit 5
    python3 tools/process_cold_calls.py post --lead-id UUID      # post formatted note

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY
    PIPEDRIVE_COMPANY_DOMAIN
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / 'projects' / 'eps' / '.tmp'

# --- Constants ---

FILTER_ID_RECENTLY_CALLED = '11215'
ALLEN_USER_ID = 23603962
PAGE_SIZE = 100
API_DELAY = 0.25

# Activity key → display name
ACTIVITY_MAP = {
    'cold__no_answer_1':          'Cold - No Answer 1',
    'cold__no_answer_2':          'Cold - No Answer 2',
    'cold__no_answer_3':          'Cold - No Answer 3',
    'cold__number_invalid':       'Cold - Invalid Number',
    'cold__not_interested':       'Cold - Not Interested / Not Qualified',
    'cold___email_sent':          'Cold - Asked For Email',
    'cold___call_back':           'Cold - Call Back',
    'cold___late_follow_up':      'Cold - Late Follow Up',
    'cold___hot_lead':            'Cold - Warm Interest',
    'cold___interested__appt_se': 'Cold - Converted To Deal',
}

# Activity types that need email drafts
EMAIL_TYPES = {'Cold - Asked For Email', 'Cold - Warm Interest'}

# Activity types where Allen actually spoke to someone
CONNECTED_TYPES = {
    'Cold - Not Interested / Not Qualified',
    'Cold - Asked For Email',
    'Cold - Call Back',
    'Cold - Late Follow Up',
    'Cold - Warm Interest',
    'Cold - Converted To Deal',
}


# --- Env & API helpers (same pattern as qualify_cold_leads.py) ---

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


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
            print("  Rate limited, waiting 2s...", file=sys.stderr)
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read())
        else:
            print(f"ERROR: API GET {path} returned {e.code}", file=sys.stderr)
            return None
    if not data.get('success'):
        print(f"ERROR: API GET {path}: {data}", file=sys.stderr)
        return None
    return data


def api_post(path, payload, *, api_key, domain):
    url = f"https://{domain}/v1{path}?api_token={api_key}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: API POST {path} returned {e.code}", file=sys.stderr)
        return None
    if not data.get('success'):
        print(f"ERROR: API POST {path}: {data}", file=sys.stderr)
        return None
    return data


# --- Fetch helpers ---

def fetch_all_leads(*, api_key, domain, limit):
    """Fetch leads from the Recently Called filter with pagination."""
    all_leads = []
    start = 0
    while True:
        data = api_get('/leads', {
            'filter_id': FILTER_ID_RECENTLY_CALLED,
            'limit': PAGE_SIZE,
            'start': start,
        }, api_key=api_key, domain=domain)
        if not data or not data.get('data'):
            break
        all_leads.extend(data['data'])
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination['next_start']
        if limit and len(all_leads) >= limit:
            all_leads = all_leads[:limit]
            break
        time.sleep(API_DELAY)
    return all_leads


def get_latest_activity(person_id, *, api_key, domain):
    """Get the most recent cold call activity for a person."""
    time.sleep(API_DELAY)
    # Fetch recent activities and find the first one that's a cold call type
    data = api_get('/activities', {
        'person_id': person_id,
        'user_id': ALLEN_USER_ID,
        'done': 1,
        'limit': 10,
        'sort': 'due_date DESC',
    }, api_key=api_key, domain=domain)
    if not data or not data.get('data'):
        return None, None
    for activity in data['data']:
        activity_key = activity.get('type', '')
        if activity_key in ACTIVITY_MAP:
            activity_type = ACTIVITY_MAP[activity_key]
            return activity_type, activity
    # Fallback: return the most recent activity even if not a cold type
    activity = data['data'][0]
    activity_key = activity.get('type', '')
    activity_type = ACTIVITY_MAP.get(activity_key, activity_key)
    return activity_type, activity


def get_latest_note(person_id, *, api_key, domain):
    """Get the most recent note on a person."""
    time.sleep(API_DELAY)
    data = api_get('/notes', {
        'person_id': person_id,
        'sort': 'add_time DESC',
        'limit': 1,
    }, api_key=api_key, domain=domain)
    if not data or not data.get('data'):
        return None
    note = data['data'][0]
    content = note.get('content', '')
    # Strip HTML tags and entities
    content = re.sub(r'<[^>]+>', '', content)
    content = content.replace('&nbsp;', ' ').replace('&amp;', '&')
    content = content.replace('&lt;', '<').replace('&gt;', '>')
    content = re.sub(r'&#\d+;', '', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content


def get_person(person_id, *, api_key, domain):
    """Fetch person details."""
    time.sleep(API_DELAY)
    data = api_get(f'/persons/{person_id}', api_key=api_key, domain=domain)
    if not data or not data.get('data'):
        return {}
    return data['data']


def get_org(org_id, *, api_key, domain):
    """Fetch org details."""
    time.sleep(API_DELAY)
    data = api_get(f'/organizations/{org_id}', api_key=api_key, domain=domain)
    if not data or not data.get('data'):
        return {}
    return data['data']


# --- Commands ---

def cmd_fetch(args, env):
    api_key = env['PIPEDRIVE_API_KEY']
    domain = env['PIPEDRIVE_COMPANY_DOMAIN']

    print(f"Fetching leads from filter {FILTER_ID_RECENTLY_CALLED}...")
    leads = fetch_all_leads(api_key=api_key, domain=domain, limit=args.limit)

    if not leads:
        print(json.dumps({"status": "empty", "count": 0, "message": "No recently called leads found."}))
        return

    print(f"Found {len(leads)} leads. Processing...\n")

    batch = []
    summary = {}

    for i, lead in enumerate(leads, 1):
        lead_id = lead['id']
        lead_title = lead.get('title', 'Unknown')
        person_id = lead.get('person_id')

        if args.verbose:
            print(f"[{i}/{len(leads)}] {lead_title}")

        if not person_id:
            if args.verbose:
                print("  Skipped: no person linked")
            continue

        # Get activity type
        activity_type, activity_data = get_latest_activity(
            person_id, api_key=api_key, domain=domain
        )

        # Get Allen's free-form note
        raw_note = get_latest_note(person_id, api_key=api_key, domain=domain)

        # Get person details
        person = get_person(person_id, api_key=api_key, domain=domain)
        person_name = person.get('name', '')
        person_email = ''
        for e in person.get('email', []):
            if e.get('value'):
                person_email = e['value']
                break
        person_phone = ''
        for p in person.get('phone', []):
            if p.get('value'):
                person_phone = p['value']
                break

        # Get org name
        org_name = ''
        org_id = person.get('org_id')
        if isinstance(org_id, dict):
            org_name = org_id.get('name', '')
        elif org_id:
            org = get_org(org_id, api_key=api_key, domain=domain)
            org_name = org.get('name', '')

        # Skip non-connected leads if --connected-only
        if args.connected_only and activity_type not in CONNECTED_TYPES:
            if args.verbose:
                print(f"  Skipped: not connected ({activity_type})")
            continue

        needs_email = activity_type in EMAIL_TYPES

        entry = {
            "lead_id": lead_id,
            "lead_title": lead_title,
            "person_id": person_id,
            "person_name": person_name,
            "person_email": person_email,
            "person_phone": person_phone,
            "org_name": org_name,
            "activity_type": activity_type or "Unknown",
            "raw_note": raw_note or "",
            "needs_email": needs_email,
        }
        batch.append(entry)

        # Track summary
        at = activity_type or "Unknown"
        summary[at] = summary.get(at, 0) + 1

        if args.verbose:
            print(f"  Activity: {activity_type}")
            print(f"  Note: {(raw_note or '')[:80]}...")
            if needs_email:
                print("  → Email draft needed")

    # Write batch file
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    batch_file = TMP_DIR / 'cold_call_batch.json'

    if not args.dry_run:
        batch_file.write_text(json.dumps(batch, indent=2))

    result = {
        "status": "ok",
        "count": len(batch),
        "batch_file": str(batch_file),
        "emails_needed": sum(1 for b in batch if b['needs_email']),
        "summary": summary,
    }
    print(json.dumps(result, indent=2))


def cmd_post(args, env):
    api_key = env['PIPEDRIVE_API_KEY']
    domain = env['PIPEDRIVE_COMPANY_DOMAIN']

    lead_id = args.lead_id
    output_file = TMP_DIR / f'cold_call_lead_{lead_id}.json'

    if not output_file.exists():
        print(f"ERROR: No output file found at {output_file}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(output_file.read_text())
    person_id = data.get('person_id')
    formatted_note = data.get('formatted_note', '')
    lead_title = data.get('lead_title', '')

    if not person_id or not formatted_note:
        print(f"ERROR: Missing person_id or formatted_note in {output_file}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would post note to person #{person_id} ({lead_title})")
        print(f"[DRY RUN] Note length: {len(formatted_note)} chars")
        return

    # Post formatted note to person
    result = api_post('/notes', {
        'content': formatted_note,
        'person_id': person_id,
        'pinned_to_person_flag': 1,
    }, api_key=api_key, domain=domain)

    if result:
        print(f"Posted note to person #{person_id} ({lead_title})")
    else:
        print(f"ERROR: Failed to post note for {lead_title}", file=sys.stderr)
        sys.exit(1)

    # Save email draft to tmp if present (for Allen's review)
    email_draft = data.get('email_draft')
    if email_draft:
        email_file = TMP_DIR / f'cold_email_{lead_id}.json'
        email_file.write_text(json.dumps(email_draft, indent=2))
        print(f"Email draft saved: {email_file}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Process cold call leads after a calling session"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # fetch
    fetch_p = subparsers.add_parser('fetch', help='Fetch recently called leads')
    fetch_p.add_argument('--dry-run', action='store_true', help='Preview only')
    fetch_p.add_argument('--limit', type=int, default=0, help='Max leads (0 = all)')
    fetch_p.add_argument('--connected-only', action='store_true', help='Only include leads where Allen spoke to someone')
    fetch_p.add_argument('--verbose', action='store_true', help='Detailed output')

    # post
    post_p = subparsers.add_parser('post', help='Post formatted note for a lead')
    post_p.add_argument('--lead-id', required=True, help='Pipedrive lead UUID')
    post_p.add_argument('--dry-run', action='store_true', help='Preview only')
    post_p.add_argument('--verbose', action='store_true', help='Detailed output')

    args = parser.parse_args()

    env = load_env()
    for key in ('PIPEDRIVE_API_KEY', 'PIPEDRIVE_COMPANY_DOMAIN'):
        if not env.get(key):
            print(f"ERROR: {key} not set in projects/eps/.env", file=sys.stderr)
            sys.exit(1)

    if args.command == 'fetch':
        cmd_fetch(args, env)
    elif args.command == 'post':
        cmd_post(args, env)


if __name__ == '__main__':
    main()
