"""
Pipedrive Activities — fast CLI for fetching and bulk-updating activities.

Usage:
    python3 tools/pipedrive_activities.py                          # today's activities, JSON
    python3 tools/pipedrive_activities.py --print                  # human-readable
    python3 tools/pipedrive_activities.py --date 2026-04-11        # specific date
    python3 tools/pipedrive_activities.py --subject "PREVIOUS"     # filter by subject substring
    python3 tools/pipedrive_activities.py --move-to 2026-04-12     # bulk move filtered results
    python3 tools/pipedrive_activities.py --done                   # only completed
    python3 tools/pipedrive_activities.py --undone                 # only pending (default: all)

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY
    PIPEDRIVE_COMPANY_DOMAIN
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'pipedrive_activities.json'

API_DELAY = 0.15


def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def api_get(path, params, *, api_key, domain):
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


def api_put(path, payload, *, api_key, domain):
    url = f"https://{domain}/v1{path}?api_token={api_key}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: API PUT {path} returned {e.code}", file=sys.stderr)
        return None


def fetch_all_activities(*, api_key, domain, start_date, end_date=None, done=None):
    """Fetch all activities for a date range with pagination.
    Uses a 3-day window to work around Pipedrive single-day query quirks,
    then filters client-side to the exact requested range."""
    target_start = start_date
    target_end = end_date or start_date
    # Widen API window by ±1 day to catch edge cases
    from datetime import timedelta
    wide_start = (datetime.strptime(target_start, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    wide_end = (datetime.strptime(target_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    params = {'limit': 500, 'start_date': wide_start, 'end_date': wide_end}
    if done is not None:
        params['done'] = int(done)
    all_items = []
    start = 0
    while True:
        params['start'] = start
        data = api_get('/activities', params, api_key=api_key, domain=domain)
        if not data:
            break
        items = data.get('data') or []
        all_items.extend(items)
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination.get('next_start', start + 500)
        time.sleep(API_DELAY)
    # Filter to exact requested date range
    all_items = [a for a in all_items if target_start <= (a.get('due_date') or '') <= target_end]
    return all_items


def bulk_move(activity_ids, new_date, *, api_key, domain):
    """Move activities to a new due date. Returns (success_count, fail_count)."""
    ok, fail = 0, 0
    for aid in activity_ids:
        result = api_put(f'/activities/{aid}', {'due_date': new_date}, api_key=api_key, domain=domain)
        if result and result.get('success'):
            ok += 1
        else:
            fail += 1
        time.sleep(API_DELAY)
    return ok, fail


def format_activity(act):
    """Extract clean fields from a raw activity."""
    return {
        'id': act['id'],
        'subject': act.get('subject', ''),
        'type': act.get('type', ''),
        'person_name': act.get('person_name', ''),
        'deal_title': act.get('deal_title', ''),
        'deal_id': act.get('deal_id'),
        'due_date': act.get('due_date', ''),
        'due_time': act.get('due_time', ''),
        'done': bool(act.get('done')),
        'note': act.get('note', ''),
        'org_name': act.get('org_name', ''),
        'owner_name': act.get('owner_name', ''),
    }


def print_activities(activities, grouped=True):
    """Print activities grouped by subject."""
    if not activities:
        print("No activities found.")
        return

    if grouped:
        by_subject = {}
        for a in activities:
            subj = a['subject'] or '(no subject)'
            by_subject.setdefault(subj, []).append(a)

        for subj, acts in sorted(by_subject.items(), key=lambda x: -len(x[1])):
            done_count = sum(1 for a in acts if a['done'])
            print(f"\n[{subj}] — {len(acts)} activities ({done_count} done, {len(acts) - done_count} pending)")
            for a in acts:
                status = 'DONE' if a['done'] else 'TODO'
                name = a['person_name'] or a['deal_title'] or a['org_name'] or '—'
                print(f"  {status}  {a['id']}  {name}")
    else:
        for a in activities:
            status = 'DONE' if a['done'] else 'TODO'
            name = a['person_name'] or a['deal_title'] or a['org_name'] or '—'
            print(f"  {status}  {a['id']}  {a['subject'] or '—'}  |  {name}")

    print(f"\nTotal: {len(activities)}")


def main():
    parser = argparse.ArgumentParser(description='Pipedrive activity tool')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'), help='Date to fetch (default: today)')
    parser.add_argument('--subject', help='Filter by subject substring (case-insensitive)')
    parser.add_argument('--type', help='Filter by activity type')
    parser.add_argument('--done', action='store_true', help='Only completed activities')
    parser.add_argument('--undone', action='store_true', help='Only pending activities')
    parser.add_argument('--move-to', help='Bulk move filtered activities to this date (YYYY-MM-DD)')
    parser.add_argument('--print', dest='print_mode', action='store_true', help='Human-readable output')
    parser.add_argument('--flat', action='store_true', help='Flat list instead of grouped by subject')
    args = parser.parse_args()

    env = load_env()
    api_key = env['PIPEDRIVE_API_KEY']
    domain = env['PIPEDRIVE_COMPANY_DOMAIN']

    done_filter = None
    if args.done:
        done_filter = True
    elif args.undone:
        done_filter = False

    raw = fetch_all_activities(api_key=api_key, domain=domain, start_date=args.date, done=done_filter)
    activities = [format_activity(a) for a in raw]

    # Apply filters
    if args.subject:
        needle = args.subject.lower()
        activities = [a for a in activities if needle in (a['subject'] or '').lower()]

    if args.type:
        needle = args.type.lower()
        activities = [a for a in activities if needle in (a['type'] or '').lower()]

    # Bulk move
    if args.move_to:
        ids = [a['id'] for a in activities]
        print(f"Moving {len(ids)} activities to {args.move_to}...")
        ok, fail = bulk_move(ids, args.move_to, api_key=api_key, domain=domain)
        print(f"Done: {ok} moved, {fail} failed")
        return

    # Output
    if args.print_mode:
        print_activities(activities, grouped=not args.flat)
    else:
        TMP_DIR.mkdir(exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(activities, f, indent=2)
        print(f"{len(activities)} activities written to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
