"""
reengage_campaign.py — Re-engagement engine for EPS.

Scans for repeat business opportunities + lost deal win-backs.
Drafts template emails, outputs candidates for Allen to review.

Usage:
    python3 tools/reengage_campaign.py --mode clients    # repeat business
    python3 tools/reengage_campaign.py --mode lost        # win-back lost deals
    python3 tools/reengage_campaign.py --mode all         # both
    python3 tools/reengage_campaign.py --dry-run          # preview only
    python3 tools/reengage_campaign.py --send             # send approved emails

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN
    PIPEDRIVE_FROM_EMAIL, GMAIL_FROM_NAME
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / '.tmp'
CLIENTS_FILE = TMP_DIR / 'reengage_clients.json'
LOST_FILE = TMP_DIR / 'reengage_lost.json'

# --- Pipedrive Projects Board/Phase IDs ---
# Board 3: EPS Clean Re-engagement
# Board 5: EPS Paint Re-engagement
REENGAGE_BOARDS = {
    3: 'EPS Clean — Re-engagement',
    5: 'EPS Paint — Re-engagement',
}

# Phases where clients need outreach
NEW_FOR_REVIEW_PHASES = {13, 29}  # "New / For Review" on boards 3 and 5

# Projects boards — completed projects that should move to re-engagement
PROJECTS_BOARDS = {
    1: 'EPS Clean Projects',
    2: 'EPS Paint Projects',
}
COMPLETED_PHASES = {1, 11}  # "Completed" on boards 1 and 2
FINAL_INVOICE_PHASES = {6, 25}  # "Final Invoice" on boards 1 and 2

# Skip list — reasons to exclude from lost deal win-back
SKIP_LOSS_REASONS = {
    'project cancelled',
    'not going ahead',
    'duplicate',
}

LOST_DEAL_LOOKBACK_DAYS = 180  # 6 months


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
API_KEY = ENV.get('PIPEDRIVE_API_KEY', '')
DOMAIN = ENV.get('PIPEDRIVE_COMPANY_DOMAIN', '')
FROM_EMAIL = ENV.get('PIPEDRIVE_FROM_EMAIL', 'sales@epsolution.com.au')
FROM_NAME = ENV.get('GMAIL_FROM_NAME', 'Allen @ EPS')


# --- Pipedrive API ---

def api_get(path, params=None):
    params = params or {}
    params['api_token'] = API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"https://{DOMAIN}/api/v1{path}?{qs}"
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


def paginate(path, params=None):
    params = params or {}
    params['limit'] = 100
    start = 0
    all_items = []
    while True:
        params['start'] = start
        data = api_get(path, params)
        if not data:
            break
        items = data.get('data') or []
        all_items.extend(items)
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination.get('next_start', start + 100)
        time.sleep(0.25)
    return all_items


# --- Email Templates ---

TEMPLATES = {
    'client_checkin': {
        'subject': 'Quick check-in — {job_type} at {address}',
        'body': (
            "Hi {first_name},\n\n"
            "Just wanted to check in after the {job_type} work we did at {address}.\n\n"
            "Hope everything is looking great. If you need anything touched up or "
            "have any upcoming projects, we'd love to help again.\n\n"
            "Cheers,\nAllen\nEPS Painting & Cleaning"
        ),
    },
    'review_ask': {
        'subject': 'Quick favour — would you leave us a review?',
        'body': (
            "Hi {first_name},\n\n"
            "Glad the {job_type} work at {address} went well.\n\n"
            "Would you mind leaving us a quick Google review? It really helps "
            "us out. Here's the link:\n\n"
            "{review_link}\n\n"
            "Thanks heaps,\nAllen\nEPS Painting & Cleaning"
        ),
    },
    'lost_winback': {
        'subject': 'Has anything changed? — {job_type} at {address}',
        'body': (
            "Hi {first_name},\n\n"
            "We quoted on {job_type} work at {address} a while back. "
            "Just wondering if anything has changed or if the project is "
            "still on the cards?\n\n"
            "Happy to re-quote if anything has shifted.\n\n"
            "Cheers,\nAllen\nEPS Painting & Cleaning"
        ),
    },
}

# EPS Google Review link
REVIEW_LINK = "https://g.page/r/CQzB9XXXXXXX/review"  # TODO: replace with real link


# --- Client Mode ---

def scan_clients():
    """Find re-engagement candidates from Pipedrive Projects."""
    print("\n=== SCANNING: Previous Clients ===")

    candidates = []

    # 1. Projects in "New / For Review" on re-engagement boards
    projects = api_get('/projects', {'limit': 500})
    if projects and projects.get('data'):
        for proj in projects['data']:
            board_id = proj.get('board_id')
            phase_id = proj.get('phase_id')

            if board_id in REENGAGE_BOARDS and phase_id in NEW_FOR_REVIEW_PHASES:
                # Get linked deal for context
                deal_ids = proj.get('deal_ids', [])
                deal_info = {}
                if deal_ids:
                    deal_data = api_get(f'/deals/{deal_ids[0]}')
                    if deal_data and deal_data.get('data'):
                        deal_info = deal_data['data']
                    time.sleep(0.25)

                # Get person info
                person_id = proj.get('person_id')
                person = {}
                if person_id:
                    person_data = api_get(f'/persons/{person_id}')
                    if person_data and person_data.get('data'):
                        person = person_data['data']
                    time.sleep(0.25)

                email = ''
                if person.get('email'):
                    for e in person['email']:
                        if isinstance(e, dict) and e.get('value'):
                            email = e['value']
                            break

                candidates.append({
                    'source': 'reengage_board',
                    'project_id': proj['id'],
                    'project_title': proj.get('title', 'Unknown'),
                    'board': REENGAGE_BOARDS.get(board_id, f'Board {board_id}'),
                    'person_name': person.get('name', proj.get('title', 'Client')),
                    'first_name': (person.get('first_name') or proj.get('title', 'there')).split()[0],
                    'email': email,
                    'deal_id': deal_ids[0] if deal_ids else None,
                    'deal_title': deal_info.get('title', ''),
                    'address': deal_info.get('org_id', {}).get('address', '') if isinstance(deal_info.get('org_id'), dict) else '',
                    'job_type': 'painting & cleaning',
                    'template': 'client_checkin',
                })

    print(f"  Found {len(candidates)} candidates")
    return candidates


def scan_lost_deals():
    """Find lost deals worth re-quoting."""
    print("\n=== SCANNING: Lost Deals ===")

    cutoff = (datetime.now() - timedelta(days=LOST_DEAL_LOOKBACK_DAYS)).strftime('%Y-%m-%d')

    # Fetch lost deals
    data = api_get('/deals', {'status': 'lost', 'sort': 'lost_time DESC', 'limit': 500})
    if not data or not data.get('data'):
        print("  No lost deals found")
        return []

    candidates = []
    for deal in data['data']:
        lost_time = deal.get('lost_time', '')
        if not lost_time or lost_time[:10] < cutoff:
            continue

        # Check loss reason
        lost_reason = (deal.get('lost_reason') or '').lower().strip()
        if lost_reason in SKIP_LOSS_REASONS:
            continue

        # Get person info
        person = deal.get('person_id')
        person_name = ''
        email = ''
        first_name = 'there'

        if isinstance(person, dict):
            person_name = person.get('name', '')
            first_name = person_name.split()[0] if person_name else 'there'
            # Need to fetch person for email
            pid = person.get('value')
            if pid:
                pdata = api_get(f'/persons/{pid}')
                if pdata and pdata.get('data'):
                    for e in (pdata['data'].get('email') or []):
                        if isinstance(e, dict) and e.get('value'):
                            email = e['value']
                            break
                time.sleep(0.25)

        # Extract address
        address = ''
        org = deal.get('org_id')
        if isinstance(org, dict):
            address = org.get('address', '') or ''

        # Determine job type from title
        title = deal.get('title', '')
        job_type = 'painting' if 'paint' in title.lower() else 'cleaning' if 'clean' in title.lower() else 'painting & cleaning'

        candidates.append({
            'source': 'lost_deal',
            'deal_id': deal['id'],
            'deal_title': title,
            'person_name': person_name,
            'first_name': first_name,
            'email': email,
            'address': address,
            'job_type': job_type,
            'lost_time': lost_time[:10],
            'lost_reason': lost_reason or '(no reason logged)',
            'value': deal.get('value') or 0,
            'template': 'lost_winback',
        })

    print(f"  Found {len(candidates)} lost deals (last {LOST_DEAL_LOOKBACK_DAYS} days)")
    return candidates


def draft_emails(candidates):
    """Draft emails from templates for each candidate."""
    drafts = []
    for c in candidates:
        template = TEMPLATES.get(c.get('template', 'client_checkin'))
        if not template:
            continue

        if not c.get('email'):
            c['draft_status'] = 'NO_EMAIL'
            drafts.append(c)
            continue

        subject = template['subject'].format(
            first_name=c.get('first_name', 'there'),
            job_type=c.get('job_type', 'the'),
            address=c.get('address', 'your property'),
        )
        body = template['body'].format(
            first_name=c.get('first_name', 'there'),
            job_type=c.get('job_type', 'the'),
            address=c.get('address', 'your property'),
            review_link=REVIEW_LINK,
        )

        c['draft_subject'] = subject
        c['draft_body'] = body
        c['draft_status'] = 'READY'
        drafts.append(c)

    ready = sum(1 for d in drafts if d.get('draft_status') == 'READY')
    no_email = sum(1 for d in drafts if d.get('draft_status') == 'NO_EMAIL')
    print(f"  Drafts: {ready} ready, {no_email} missing email")
    return drafts


def send_approved(candidates, dry_run=False):
    """Send emails for approved candidates."""
    sent = 0
    for c in candidates:
        if c.get('draft_status') != 'READY':
            continue
        if not c.get('approved', False):
            continue

        cmd = [
            'python3', str(BASE_DIR / 'tools' / 'send_email_gmail.py'),
            '--to', c['email'],
            '--subject', c['draft_subject'],
            '--body', c['draft_body'],
        ]
        if c.get('deal_id'):
            cmd.extend(['--deal-id', str(c['deal_id'])])

        if dry_run:
            print(f"  [DRY RUN] Would send to {c['email']}: {c['draft_subject']}")
            sent += 1
            continue

        print(f"  Sending to {c['email']}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            sent += 1
            c['sent'] = True
        else:
            print(f"    FAILED: {result.stderr[:200]}")
            c['sent'] = False

    return sent


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="EPS Re-engagement Campaign")
    parser.add_argument('--mode', choices=['clients', 'lost', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--send', action='store_true', help='Send approved emails')
    args = parser.parse_args()

    if not API_KEY or not DOMAIN:
        print("ERROR: Set PIPEDRIVE_API_KEY and PIPEDRIVE_COMPANY_DOMAIN in projects/eps/.env")
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"EPS Re-engagement Campaign — {timestamp}")
    if args.dry_run:
        print("*** DRY RUN ***")

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Scan
    if args.mode in ('clients', 'all'):
        clients = scan_clients()
        clients = draft_emails(clients)
        CLIENTS_FILE.write_text(json.dumps(clients, indent=2, default=str))
        print(f"\n  Saved to {CLIENTS_FILE}")

    if args.mode in ('lost', 'all'):
        lost = scan_lost_deals()
        lost = draft_emails(lost)
        LOST_FILE.write_text(json.dumps(lost, indent=2, default=str))
        print(f"\n  Saved to {LOST_FILE}")

    # Summary
    print(f"\n{'='*50}")
    print(f"  RE-ENGAGEMENT SUMMARY — {timestamp}")
    print(f"{'='*50}")

    if args.mode in ('clients', 'all') and clients:
        ready = sum(1 for c in clients if c.get('draft_status') == 'READY')
        print(f"  Previous clients:  {len(clients)} found, {ready} emails ready")

    if args.mode in ('lost', 'all') and lost:
        ready = sum(1 for c in lost if c.get('draft_status') == 'READY')
        total_value = sum(c.get('value', 0) for c in lost)
        print(f"  Lost deals:        {len(lost)} found, {ready} emails ready")
        print(f"  Lost deal value:   ${total_value:,.0f}")

    print(f"{'='*50}")

    # Send if requested
    if args.send:
        print("\nSending approved emails...")
        if args.mode in ('clients', 'all') and clients:
            sent = send_approved(clients, args.dry_run)
            print(f"  Client emails sent: {sent}")
        if args.mode in ('lost', 'all') and lost:
            sent = send_approved(lost, args.dry_run)
            print(f"  Win-back emails sent: {sent}")


if __name__ == '__main__':
    main()
