"""
eod_ops_manager.py — End-of-Day Operations Manager.

Scans all Pipedrive deals and projects, builds per-deal context files,
identifies what needs attention, and queues questions for Allen.

Runs daily at EOD. Zero LLM cost — pure Pipedrive API + logic.

Usage:
    python3 tools/eod_ops_manager.py               # full scan
    python3 tools/eod_ops_manager.py --print        # human-readable report
    python3 tools/eod_ops_manager.py --deal-id 1302 # scan one deal
    python3 tools/eod_ops_manager.py --dry-run      # preview, no file writes

Output:
    projects/eps/.tmp/deals/{deal_id}.json     — per-deal context
    projects/eps/.tmp/projects/{project_id}.json — per-project context
    .tmp/pending_questions.json                — questions for Allen
    .tmp/eod_report.json                       — full scan report

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN
"""

import argparse
import json
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
DEALS_DIR = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'deals'
PROJECTS_DIR = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'projects'
QUESTIONS_FILE = TMP_DIR / 'pending_questions.json'
REPORT_FILE = TMP_DIR / 'eod_report.json'

API_DELAY = 0.25

# --- Pipeline / Stage config ---
PIPELINES = {
    1: 'EPS Clean', 2: 'EPS Paint',
    3: 'Tenders - Clean', 4: 'Tenders - Paint',
}

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
}

# What should happen next at each stage
NEXT_ACTION_RULES = {
    'NEW': ('Schedule site visit or start quoting', 3),
    'SITE VISIT': ('Confirm SM8 job created, book visit', 2),
    'QUOTE IN PROGRESS': ('Finish and send quote', 5),
    'QUOTE SENT': ('Follow up — call first, then email', 2),
    'FOLLOW UP': ('Chase response — call then email', 3),
    'CONTACT MADE': ('Continue negotiation', 3),
    'NEGOTIATION / FOLLOW UP': ('Follow up on negotiation', 3),
    'LATE FOLLOW UP': ('Final follow-up — email nudge', 5),
    'DEPOSIT PROCESS': ('Collect deposit — urgent', 1),
}

# Project phases
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

PROJECT_BOARDS = {
    1: 'EPS Clean Projects', 2: 'EPS Paint Projects',
    3: 'Clean Re-engagement', 5: 'Paint Re-engagement',
}

PROJECT_NEXT_ACTIONS = {
    'New': ('Book the job on SM8', 2),
    'Pending Booking': ('Confirm booking date with client', 2),
    'Booked': ('Monitor — job in progress', 0),
    'Fixups': ('Schedule fix-up visit', 2),
    'Fix Ups': ('Schedule fix-up visit', 2),
    'Completed': ('Send final invoice', 3),
    'Variations': ('Quote and invoice variations', 3),
    'Final Invoice': ('Confirm payment received', 5),
    'Forward to Google Review': ('Move to re-engagement board', 2),
}

SM8_JOB_FIELD = "052a8b8271d035ca4780f8ae06cd7b5370df544c"
ADDRESS_FIELD = "3f2f0aac01d1e42e63b60cee0c781c80e85f1e90"


# --- Env + API ---

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


def api_get(path, params=None):
    params = params or {}
    params['api_token'] = API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"https://{DOMAIN}/api/v1{path}?{qs}"
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                return json.loads(r.read())
        return None


def paginate(path, params=None):
    params = params or {}
    params['limit'] = 100
    start = 0
    items = []
    while True:
        params['start'] = start
        data = api_get(path, params)
        if not data:
            break
        items.extend(data.get('data') or [])
        pag = data.get('additional_data', {}).get('pagination', {})
        if not pag.get('more_items_in_collection'):
            break
        start = pag.get('next_start', start + 100)
        time.sleep(API_DELAY)
    return items


def get_last_activity_date(deal):
    for field in ('last_activity_date', 'update_time', 'stage_change_time'):
        val = deal.get(field)
        if val:
            return val[:10]
    return None


# --- Deal Processing ---

def process_deal(deal, today_str, today_dt):
    """Build context summary for a single deal."""
    did = deal['id']
    stage_id = deal.get('stage_id')
    stage_info = STAGES.get(stage_id, ('UNKNOWN', 0))
    stage_name, pipeline_id = stage_info
    pipeline_name = PIPELINES.get(pipeline_id, 'Unknown')

    # Extract person info
    person = deal.get('person_id')
    person_name = ''
    person_email = ''
    if isinstance(person, dict):
        person_name = person.get('name', '')
        emails = person.get('email', [])
        if isinstance(emails, list):
            for e in emails:
                if isinstance(e, dict) and e.get('value'):
                    person_email = e['value']
                    break
        elif isinstance(emails, str):
            person_email = emails

    # Extract org
    org = deal.get('org_id')
    org_name = org.get('name', '') if isinstance(org, dict) else ''

    # Address
    address = deal.get(ADDRESS_FIELD, '') or ''
    if not address and isinstance(org, dict):
        address = org.get('address', '') or ''

    # SM8 job number
    sm8_job = (deal.get(SM8_JOB_FIELD) or '').strip()

    # Last activity
    last_activity = get_last_activity_date(deal)
    days_since = 0
    if last_activity:
        try:
            days_since = (today_dt - datetime.strptime(last_activity, '%Y-%m-%d')).days
        except ValueError:
            pass

    # Next action
    next_action, max_days = NEXT_ACTION_RULES.get(stage_name, ('Review deal', 7))

    # Flags
    flags = []
    questions = []

    # Overdue check
    if days_since > max_days:
        flags.append(f"OVERDUE: {days_since} days since last activity (max {max_days})")

    # Stage-specific checks
    if stage_name == 'DEPOSIT PROCESS' and not sm8_job:
        flags.append("IN DEPOSIT but no SM8 Job # linked")
        questions.append("Deal in DEPOSIT but no SM8 job. Was the job created on SM8?")

    if stage_name in ('QUOTE SENT', 'FOLLOW UP') and days_since > 14:
        questions.append(f"Quote sent {days_since} days ago with no response. Move to LATE FOLLOW UP or mark lost?")

    if stage_name == 'NEGOTIATION / FOLLOW UP' and days_since > 30:
        questions.append(f"In NEGOTIATION for {days_since} days. Still active or mark as lost?")

    if stage_name == 'LATE FOLLOW UP' and days_since > 21:
        questions.append(f"In LATE FOLLOW UP for {days_since} days. Mark as lost?")

    if stage_name == 'SITE VISIT' and not sm8_job:
        flags.append("SITE VISIT stage but no SM8 job linked yet")

    if stage_name == 'NEW' and days_since > 5:
        flags.append(f"In NEW for {days_since} days — needs qualification")

    # Build context
    context = {
        'deal_id': did,
        'title': deal.get('title', ''),
        'client': person_name,
        'email': person_email,
        'org': org_name,
        'address': address,
        'pipeline': pipeline_name,
        'stage': stage_name,
        'stage_id': stage_id,
        'value': deal.get('value') or 0,
        'sm8_job': sm8_job,
        'last_activity': last_activity,
        'days_since_activity': days_since,
        'next_action': next_action,
        'max_days_before_overdue': max_days,
        'flags': flags,
        'updated_at': today_str,
    }

    return context, questions


def process_project(proj, today_str):
    """Build context summary for a Pipedrive project."""
    pid = proj['id']
    phase_id = proj.get('phase_id')
    board_id = proj.get('board_id')
    phase_name = PROJECT_PHASES.get(phase_id, 'Unknown')
    board_name = PROJECT_BOARDS.get(board_id, f'Board {board_id}')

    # Person
    person_id = proj.get('person_id')

    # Linked deals
    deal_ids = proj.get('deal_ids', [])

    # Last update
    last_update = (proj.get('update_time') or proj.get('add_time') or '')[:10]

    # Next action
    next_action, max_days = PROJECT_NEXT_ACTIONS.get(phase_name, ('Review project', 7))

    flags = []
    questions = []

    # Check staleness
    if last_update:
        try:
            days_since = (datetime.strptime(today_str, '%Y-%m-%d') -
                          datetime.strptime(last_update, '%Y-%m-%d')).days
            if days_since > max_days and max_days > 0:
                flags.append(f"No update in {days_since} days (expected every {max_days})")
        except ValueError:
            days_since = 0
    else:
        days_since = 0

    if phase_name == 'Final Invoice' and days_since > 7:
        questions.append(f"Final invoice sent {days_since} days ago. Payment received?")

    if phase_name == 'Forward to Google Review' and days_since > 3:
        questions.append("Ready for Google Review sequence. Move to re-engagement board?")

    context = {
        'project_id': pid,
        'title': proj.get('title', ''),
        'board': board_name,
        'phase': phase_name,
        'phase_id': phase_id,
        'person_id': person_id,
        'deal_ids': deal_ids,
        'status': proj.get('status', ''),
        'last_update': last_update,
        'days_since_update': days_since,
        'next_action': next_action,
        'flags': flags,
        'updated_at': today_str,
    }

    return context, questions


# --- Main ---

def run_eod(deal_id=None, dry_run=False, print_mode=False):
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    timestamp = today_dt.strftime('%Y-%m-%d %H:%M')

    print(f"EOD Ops Manager — {timestamp}")
    if dry_run:
        print("*** DRY RUN ***\n")

    # Create output dirs
    if not dry_run:
        DEALS_DIR.mkdir(parents=True, exist_ok=True)
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        TMP_DIR.mkdir(parents=True, exist_ok=True)

    all_questions = []
    report = {
        'timestamp': timestamp,
        'deals': {'total': 0, 'by_pipeline': {}, 'overdue': 0, 'flagged': 0},
        'projects': {'total': 0, 'by_board': {}, 'flagged': 0},
        'questions': 0,
    }

    # --- DEALS ---
    print("Scanning deals...")
    if deal_id:
        data = api_get(f'/deals/{deal_id}')
        deals = [data['data']] if data and data.get('data') else []
    else:
        deals = []
        for pid in PIPELINES:
            pipeline_deals = paginate(f'/pipelines/{pid}/deals', {'status': 'open'})
            deals.extend(pipeline_deals)
            time.sleep(API_DELAY)

    report['deals']['total'] = len(deals)
    print(f"  {len(deals)} active deals\n")

    for deal in deals:
        context, questions = process_deal(deal, today_str, today_dt)
        did = context['deal_id']
        pipeline = context['pipeline']

        # Count by pipeline
        report['deals']['by_pipeline'][pipeline] = report['deals']['by_pipeline'].get(pipeline, 0) + 1

        # Count flags
        if context['flags']:
            report['deals']['flagged'] += 1
            if any('OVERDUE' in f for f in context['flags']):
                report['deals']['overdue'] += 1

        # Save context file
        if not dry_run:
            deal_file = DEALS_DIR / f"{did}.json"
            # Merge with existing context (preserve history fields)
            if deal_file.exists():
                try:
                    existing = json.loads(deal_file.read_text())
                    # Keep previous_stage if stage changed
                    if existing.get('stage') != context['stage']:
                        context['previous_stage'] = existing.get('stage')
                        context['stage_changed_on'] = today_str
                    elif existing.get('previous_stage'):
                        context['previous_stage'] = existing['previous_stage']
                        context['stage_changed_on'] = existing.get('stage_changed_on')
                except (json.JSONDecodeError, KeyError):
                    pass
            deal_file.write_text(json.dumps(context, indent=2))

        # Queue questions
        for q in questions:
            all_questions.append({
                'type': 'deal',
                'id': did,
                'title': context['title'],
                'stage': context['stage'],
                'question': q,
                'priority': 'high' if 'lost' in q.lower() or 'deposit' in q.lower() else 'medium',
                'created': today_str,
            })

        if print_mode and (context['flags'] or questions):
            flag_str = ' | '.join(context['flags']) if context['flags'] else ''
            print(f"  #{did} {context['title']} [{context['stage']}]")
            if flag_str:
                print(f"    FLAGS: {flag_str}")
            for q in questions:
                print(f"    QUESTION: {q}")

    # --- PROJECTS ---
    print("\nScanning projects...")
    proj_data = api_get('/projects', {'status': 'open', 'limit': 500})
    projects = (proj_data or {}).get('data') or []
    report['projects']['total'] = len(projects)
    print(f"  {len(projects)} active projects\n")

    for proj in projects:
        context, questions = process_project(proj, today_str)
        pid = context['project_id']
        board = context['board']

        report['projects']['by_board'][board] = report['projects']['by_board'].get(board, 0) + 1

        if context['flags']:
            report['projects']['flagged'] += 1

        if not dry_run:
            proj_file = PROJECTS_DIR / f"{pid}.json"
            proj_file.write_text(json.dumps(context, indent=2))

        for q in questions:
            all_questions.append({
                'type': 'project',
                'id': pid,
                'title': context['title'],
                'phase': context['phase'],
                'question': q,
                'priority': 'medium',
                'created': today_str,
            })

        if print_mode and (context['flags'] or questions):
            print(f"  Project #{pid} {context['title']} [{context['phase']}]")
            for f in context['flags']:
                print(f"    FLAG: {f}")
            for q in questions:
                print(f"    QUESTION: {q}")

    # --- Save questions ---
    report['questions'] = len(all_questions)

    if not dry_run:
        # Merge with existing questions (don't overwrite unresolved ones)
        existing_q = []
        if QUESTIONS_FILE.exists():
            try:
                existing_q = json.loads(QUESTIONS_FILE.read_text())
                # Keep unresolved questions from previous runs
                existing_q = [q for q in existing_q if q.get('resolved') != True]
            except (json.JSONDecodeError, KeyError):
                existing_q = []

        # Deduplicate — don't add same question for same deal/project
        existing_keys = {(q.get('type'), q.get('id'), q.get('question')) for q in existing_q}
        new_q = [q for q in all_questions
                 if (q['type'], q['id'], q['question']) not in existing_keys]

        merged = existing_q + new_q
        QUESTIONS_FILE.write_text(json.dumps(merged, indent=2))
        REPORT_FILE.write_text(json.dumps(report, indent=2))

    # --- Summary ---
    print(f"\n{'='*55}")
    print(f"  EOD OPS REPORT — {timestamp}")
    print(f"{'='*55}")
    print(f"  DEALS")
    print(f"    Total active:    {report['deals']['total']}")
    for pname, count in report['deals']['by_pipeline'].items():
        print(f"      {pname}: {count}")
    print(f"    Overdue:         {report['deals']['overdue']}")
    print(f"    Flagged:         {report['deals']['flagged']}")
    print(f"  PROJECTS")
    print(f"    Total active:    {report['projects']['total']}")
    for bname, count in report['projects']['by_board'].items():
        print(f"      {bname}: {count}")
    print(f"    Flagged:         {report['projects']['flagged']}")
    print(f"  QUESTIONS:         {report['questions']}")
    print(f"{'='*55}")

    if all_questions:
        print(f"\n  Questions for Allen:")
        high = [q for q in all_questions if q['priority'] == 'high']
        medium = [q for q in all_questions if q['priority'] == 'medium']
        for q in high:
            print(f"    [HIGH] #{q['id']} {q['title']}: {q['question']}")
        for q in medium[:5]:
            print(f"    [MED]  #{q['id']} {q['title']}: {q['question']}")
        if len(medium) > 5:
            print(f"    ... and {len(medium) - 5} more medium-priority questions")

    if not dry_run:
        print(f"\n  Context files: {DEALS_DIR}/ ({report['deals']['total']} deals)")
        print(f"                 {PROJECTS_DIR}/ ({report['projects']['total']} projects)")
        print(f"  Questions:     {QUESTIONS_FILE}")

    return report


def main():
    parser = argparse.ArgumentParser(description="EOD Ops Manager — scan deals + projects")
    parser.add_argument('--print', action='store_true', dest='print_mode')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--deal-id', type=int)
    args = parser.parse_args()

    if not API_KEY or not DOMAIN:
        print("ERROR: Set PIPEDRIVE_API_KEY and PIPEDRIVE_COMPANY_DOMAIN in projects/eps/.env")
        sys.exit(1)

    run_eod(deal_id=args.deal_id, dry_run=args.dry_run,
            print_mode=args.print_mode or args.dry_run)


if __name__ == '__main__':
    main()
