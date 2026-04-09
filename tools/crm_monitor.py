"""
CRM Monitor — scans all Pipedrive pipelines and generates action items.

Checks: follow-up gaps, overdue activities, stale deals/leads, pipeline KPIs,
team performance. Pure Python, no LLM.

Usage:
    python3 tools/crm_monitor.py                  # full scan, output JSON
    python3 tools/crm_monitor.py --print           # human-readable summary
    python3 tools/crm_monitor.py --dry-run         # preview, no activities created

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
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'crm_monitor.json'

API_DELAY = 0.25

# --- Pipeline & Stage IDs ---
PIPELINES = {
    1: 'EPS Clean',
    2: 'EPS Paint',
    3: 'Tenders - Clean',
    4: 'Tenders - Paint',
}

# Stage ID → (name, pipeline_id)
STAGES = {
    22: ('NEW', 1), 3: ('SITE VISIT', 1), 24: ('QUOTE IN PROGRESS', 1),
    4: ('QUOTE SENT', 1), 18: ('NEGOTIATION / FOLLOW UP', 1),
    5: ('LATE FOLLOW UP', 1), 47: ('DEPOSIT PROCESS', 1),
    21: ('NEW', 2), 10: ('SITE VISIT', 2), 27: ('QUOTE IN PROGRESS', 2),
    11: ('QUOTE SENT', 2), 17: ('NEGOTIATION / FOLLOW UP', 2),
    12: ('LATE FOLLOW UP', 2), 48: ('DEPOSIT PROCESS', 2),
    31: ('NEW', 3), 32: ('CONTACT MADE', 3), 33: ('NEGOTIATION / FOLLOW UP', 3),
    34: ('LATE FOLLOW UP', 3),
    35: ('NEW', 4), 36: ('CONTACT MADE', 4), 37: ('NEGOTIATION / FOLLOW UP', 4),
    38: ('LATE FOLLOW UP', 4),
}

# Follow-up rules: stage_id → max days without activity before flagging
FOLLOWUP_RULES = {
    # QUOTE SENT — 2 days, call first
    4: {'max_days': 2, 'action': 'call_then_email'},
    11: {'max_days': 2, 'action': 'call_then_email'},
    # NEGOTIATION — 3 days, call first
    18: {'max_days': 3, 'action': 'call_then_email'},
    17: {'max_days': 3, 'action': 'call_then_email'},
    33: {'max_days': 3, 'action': 'call_then_email'},
    37: {'max_days': 3, 'action': 'call_then_email'},
    # LATE FOLLOW UP — 5 days, email nudge
    5: {'max_days': 5, 'action': 'email'},
    12: {'max_days': 5, 'action': 'email'},
    34: {'max_days': 5, 'action': 'email'},
    38: {'max_days': 5, 'action': 'email'},
    # CONTACT MADE (tenders) — 2 days, call then email
    32: {'max_days': 2, 'action': 'call_then_email'},
    36: {'max_days': 2, 'action': 'call_then_email'},
    # DEPOSIT PROCESS — 1 day, flag urgent
    47: {'max_days': 1, 'action': 'urgent'},
    48: {'max_days': 1, 'action': 'urgent'},
}

# Stale deal threshold
STALE_DAYS = 7

# Activity type tiers — grouped by Allen's daily schedule priority
DISCOVERY_TYPES = {'exec___clean_discovery', 'lunch'}  # lunch = Paint Discovery
CLEAN_FOLLOWUP_TYPES = {'sales__follow_up'}  # sales__follow_up = Clean Follow-Up
PAINT_FOLLOWUP_TYPES = {'exec__paint_follow_up'}
VIP_TYPES = {'exec__vip'}
OPERATIONAL_ACTIVITY_TYPES = {'task', 'meeting', 'deadline', 'discovery___call_back'}

# All exec types combined (for quick checks)
EXEC_ACTIVITY_TYPES = DISCOVERY_TYPES | CLEAN_FOLLOWUP_TYPES | PAINT_FOLLOWUP_TYPES | VIP_TYPES

COLD_ACTIVITY_PREFIX = 'cold__'

# Display names for activity types (Pipedrive keys → human labels)
ACTIVITY_TYPE_NAMES = {
    'exec___clean_discovery': 'Clean Discovery',
    'lunch': 'Paint Discovery',
    'sales__follow_up': 'Clean Follow-Up',
    'exec__paint_follow_up': 'Paint Follow-Up',
    'exec__vip': 'VIP',
    'task': 'Task',
    'meeting': 'Site Visit',
    'deadline': 'Quote',
    'discovery___call_back': 'System Improvements',
}


# --- Env & API helpers (reused from qualify_cold_leads.py) ---

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


def paginate_all(path, params=None, *, api_key, domain, limit=100):
    """Fetch all pages from a paginated Pipedrive endpoint."""
    params = params or {}
    params['limit'] = limit
    start = 0
    all_items = []
    while True:
        params['start'] = start
        data = api_get(path, params, api_key=api_key, domain=domain)
        if not data:
            break
        items = data.get('data') or []
        all_items.extend(items)
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination.get('next_start', start + limit)
        time.sleep(API_DELAY)
    return all_items


# --- Data fetching ---

def fetch_users(*, api_key, domain):
    data = api_get('/users', api_key=api_key, domain=domain)
    if not data:
        return []
    return [
        {'id': u['id'], 'name': u['name'], 'email': u.get('email', ''),
         'active': u.get('active_flag', False)}
        for u in (data.get('data') or [])
        if u.get('active_flag', False)
    ]


def fetch_deals_by_pipeline(pipeline_id, *, api_key, domain):
    """Fetch all open deals in a pipeline."""
    return paginate_all(
        f'/pipelines/{pipeline_id}/deals',
        {'status': 'open', 'get_summary': '0'},
        api_key=api_key, domain=domain
    )


def fetch_deals_by_status(status, start_date=None, *, api_key, domain):
    """Fetch deals by status (won/lost) optionally filtered by date."""
    params = {'status': status, 'sort': 'update_time DESC', 'limit': 500}
    data = api_get('/deals', params, api_key=api_key, domain=domain)
    if not data:
        return []
    deals = data.get('data') or []
    if start_date:
        deals = [d for d in deals if (d.get('won_time') or d.get('lost_time') or '') >= start_date]
    return deals


def fetch_activities(*, api_key, domain, user_id=None, start_date=None,
                     end_date=None, done=None):
    """Fetch activities with optional filters."""
    params = {'limit': 500}
    if user_id:
        params['user_id'] = user_id
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    if done is not None:
        params['done'] = int(done)
    data = api_get('/activities', params, api_key=api_key, domain=domain)
    if not data:
        return []
    return data.get('data') or []


def fetch_deal_flow(deal_id, *, api_key, domain):
    """Fetch deal timeline/flow to find last activity date."""
    data = api_get(f'/deals/{deal_id}/flow', api_key=api_key, domain=domain)
    if not data:
        return []
    return data.get('data') or []


def fetch_deal_activities(deal_id, *, api_key, domain):
    """Fetch activities for a specific deal."""
    data = api_get(f'/deals/{deal_id}/activities', api_key=api_key, domain=domain)
    if not data:
        return []
    return data.get('data') or []


# --- Analysis functions ---

def get_last_activity_date(deal):
    """Extract last activity date from deal data."""
    last = deal.get('last_activity_date')
    if last:
        return last
    update_time = deal.get('update_time', '')
    if update_time:
        return update_time[:10]
    return deal.get('add_time', '')[:10]


def check_follow_ups(deals, today_str):
    """Check all deals for follow-up gaps based on stage rules."""
    action_items = []
    today = datetime.strptime(today_str, '%Y-%m-%d')

    for deal in deals:
        stage_id = deal.get('stage_id')
        rule = FOLLOWUP_RULES.get(stage_id)
        if not rule:
            continue

        last_activity = get_last_activity_date(deal)
        if not last_activity:
            continue

        last_date = datetime.strptime(last_activity[:10], '%Y-%m-%d')
        days_since = (today - last_date).days

        if days_since > rule['max_days']:
            stage_name = STAGES.get(stage_id, ('UNKNOWN', 0))[0]
            pipeline_name = PIPELINES.get(STAGES.get(stage_id, ('', 0))[1], 'Unknown')
            owner_id = deal.get('user_id', {})
            if isinstance(owner_id, dict):
                owner_id = owner_id.get('id', 0)

            priority = 'URGENT' if rule['action'] == 'urgent' else (
                'HIGH' if days_since > rule['max_days'] * 2 else 'MEDIUM'
            )

            value = deal.get('value') or 0
            currency = deal.get('currency', 'AUD')

            action_items.append({
                'type': 'follow_up',
                'priority': priority,
                'deal_id': deal['id'],
                'deal_title': deal.get('title', 'Unknown'),
                'pipeline': pipeline_name,
                'stage': stage_name,
                'stage_id': stage_id,
                'owner_id': owner_id,
                'value': value,
                'currency': currency,
                'days_since_activity': days_since,
                'max_days': rule['max_days'],
                'recommended_action': rule['action'],
                'last_activity_date': last_activity[:10],
                'person_id': deal.get('person_id') if isinstance(deal.get('person_id'), int) else (deal['person_id'].get('value') if isinstance(deal.get('person_id'), dict) else None),
                'person_name': deal.get('person_name') or (deal['person_id']['name'] if isinstance(deal.get('person_id'), dict) else ''),
                'org_name': deal.get('org_name') or (deal['org_id']['name'] if isinstance(deal.get('org_id'), dict) else ''),
            })

    return action_items


def check_overdue_activities(activities, today_str):
    """Find overdue activities (due before today, not done)."""
    items = []
    for act in activities:
        if act.get('done') or not act.get('due_date'):
            continue
        if act['due_date'] < today_str:
            items.append({
                'type': 'overdue_activity',
                'priority': 'HIGH',
                'activity_id': act['id'],
                'subject': act.get('subject', ''),
                'activity_type': act.get('type', ''),
                'due_date': act['due_date'],
                'deal_id': act.get('deal_id'),
                'deal_title': act.get('deal_title', ''),
                'owner_id': act.get('user_id', 0),
                'person_name': act.get('person_name', ''),
                'days_overdue': (datetime.strptime(today_str, '%Y-%m-%d') -
                                 datetime.strptime(act['due_date'], '%Y-%m-%d')).days,
            })
    return items


def check_stale_deals(deals, today_str):
    """Find deals with no activity in STALE_DAYS."""
    items = []
    today = datetime.strptime(today_str, '%Y-%m-%d')

    for deal in deals:
        stage_id = deal.get('stage_id')
        # Skip if already covered by follow-up rules
        if stage_id in FOLLOWUP_RULES:
            continue

        last_activity = get_last_activity_date(deal)
        if not last_activity:
            continue

        last_date = datetime.strptime(last_activity[:10], '%Y-%m-%d')
        days_since = (today - last_date).days

        if days_since >= STALE_DAYS:
            stage_name = STAGES.get(stage_id, ('UNKNOWN', 0))[0]
            pipeline_name = PIPELINES.get(STAGES.get(stage_id, ('', 0))[1], 'Unknown')
            owner_id = deal.get('user_id', {})
            if isinstance(owner_id, dict):
                owner_id = owner_id.get('id', 0)

            items.append({
                'type': 'stale_deal',
                'priority': 'LOW',
                'deal_id': deal['id'],
                'deal_title': deal.get('title', 'Unknown'),
                'pipeline': pipeline_name,
                'stage': stage_name,
                'owner_id': owner_id,
                'person_id': deal.get('person_id') if isinstance(deal.get('person_id'), int) else (deal['person_id'].get('value') if isinstance(deal.get('person_id'), dict) else None),
                'person_name': deal.get('person_name') or (deal['person_id']['name'] if isinstance(deal.get('person_id'), dict) else ''),
                'days_since_activity': days_since,
                'last_activity_date': last_activity[:10],
                'value': deal.get('value') or 0,
            })

    return items


def build_pipeline_summary(all_deals):
    """Build pipeline health summary — deals and value per pipeline per stage."""
    summary = {}
    for pid, pname in PIPELINES.items():
        summary[pname] = {'total_deals': 0, 'total_value': 0, 'stages': {}}

    for deal in all_deals:
        stage_id = deal.get('stage_id')
        stage_info = STAGES.get(stage_id)
        if not stage_info:
            continue
        stage_name, pipeline_id = stage_info
        pipeline_name = PIPELINES.get(pipeline_id, 'Unknown')

        if pipeline_name not in summary:
            continue

        summary[pipeline_name]['total_deals'] += 1
        summary[pipeline_name]['total_value'] += deal.get('value') or 0

        if stage_name not in summary[pipeline_name]['stages']:
            summary[pipeline_name]['stages'][stage_name] = {'count': 0, 'value': 0}
        summary[pipeline_name]['stages'][stage_name]['count'] += 1
        summary[pipeline_name]['stages'][stage_name]['value'] += deal.get('value') or 0

    return summary


def build_team_scorecard(users, activities_done, activities_pending, all_deals):
    """Build per-rep performance metrics."""
    scorecard = {}
    for user in users:
        uid = user['id']
        scorecard[user['name']] = {
            'user_id': uid,
            'calls_this_week': 0,
            'emails_this_week': 0,
            'meetings_this_week': 0,
            'total_activities_done': 0,
            'overdue_items': 0,
            'deals_in_pipeline': 0,
            'pipeline_value': 0,
        }

    for act in activities_done:
        uid = act.get('user_id', 0)
        for name, card in scorecard.items():
            if card['user_id'] == uid:
                card['total_activities_done'] += 1
                atype = (act.get('type') or '').lower()
                if 'call' in atype:
                    card['calls_this_week'] += 1
                elif 'email' in atype or 'mail' in atype:
                    card['emails_this_week'] += 1
                elif 'meeting' in atype:
                    card['meetings_this_week'] += 1
                break

    for act in activities_pending:
        uid = act.get('user_id', 0)
        for name, card in scorecard.items():
            if card['user_id'] == uid:
                card['overdue_items'] += 1
                break

    for deal in all_deals:
        owner_id = deal.get('user_id', {})
        if isinstance(owner_id, dict):
            owner_id = owner_id.get('id', 0)
        for name, card in scorecard.items():
            if card['user_id'] == owner_id:
                card['deals_in_pipeline'] += 1
                card['pipeline_value'] += deal.get('value') or 0
                break

    return scorecard


def build_kpis(won_deals_week, lost_deals_week, won_deals_month, lost_deals_month,
               activities_done_week, all_deals):
    """Build top-line KPI summary."""
    # Count quotes sent this week (deals in QUOTE SENT stages)
    quote_sent_stages = {4, 11}
    quotes_this_week = sum(1 for d in all_deals if d.get('stage_id') in quote_sent_stages)

    # Tender stages
    tender_stages = {31, 32, 33, 34, 35, 36, 37, 38}
    tenders_active = sum(1 for d in all_deals if d.get('stage_id') in tender_stages)

    calls_this_week = sum(1 for a in activities_done_week if 'call' in (a.get('type') or '').lower())
    emails_this_week = sum(1 for a in activities_done_week if 'email' in (a.get('type') or '').lower() or 'mail' in (a.get('type') or '').lower())

    total_pipeline_value = sum(d.get('value') or 0 for d in all_deals)
    total_pipeline_deals = len(all_deals)

    won_value_week = sum(d.get('value') or 0 for d in won_deals_week)
    won_value_month = sum(d.get('value') or 0 for d in won_deals_month)
    lost_value_month = sum(d.get('value') or 0 for d in lost_deals_month)

    total_month = len(won_deals_month) + len(lost_deals_month)
    conversion_rate = (len(won_deals_month) / total_month * 100) if total_month > 0 else 0

    return {
        'pipeline_deals': total_pipeline_deals,
        'pipeline_value': total_pipeline_value,
        'quotes_in_sent': quotes_this_week,
        'tenders_active': tenders_active,
        'deals_won_week': len(won_deals_week),
        'won_value_week': won_value_week,
        'deals_won_month': len(won_deals_month),
        'won_value_month': won_value_month,
        'deals_lost_month': len(lost_deals_month),
        'lost_value_month': lost_value_month,
        'conversion_rate_month': round(conversion_rate, 1),
        'calls_this_week': calls_this_week,
        'emails_this_week': emails_this_week,
    }


# --- Main ---

def run_monitor(*, api_key, domain, dry_run=False, verbose=False):
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    month_start = today.replace(day=1).strftime('%Y-%m-%d')

    print(f"CRM Monitor — {today_str}")
    print(f"  Week start: {week_start} | Month start: {month_start}")

    # 1. Fetch users
    print("\nFetching users...")
    users = fetch_users(api_key=api_key, domain=domain)
    print(f"  Found {len(users)} active users: {', '.join(u['name'] for u in users)}")
    time.sleep(API_DELAY)

    # 2. Fetch all open deals across all pipelines
    print("\nFetching deals across all pipelines...")
    all_deals = []
    for pid, pname in PIPELINES.items():
        deals = fetch_deals_by_pipeline(pid, api_key=api_key, domain=domain)
        print(f"  {pname}: {len(deals)} open deals")
        all_deals.extend(deals)
        time.sleep(API_DELAY)

    # 3. Fetch won/lost deals
    print("\nFetching won/lost deals...")
    won_deals_week = fetch_deals_by_status('won', week_start, api_key=api_key, domain=domain)
    time.sleep(API_DELAY)
    won_deals_month = fetch_deals_by_status('won', month_start, api_key=api_key, domain=domain)
    time.sleep(API_DELAY)
    lost_deals_week = fetch_deals_by_status('lost', week_start, api_key=api_key, domain=domain)
    time.sleep(API_DELAY)
    lost_deals_month = fetch_deals_by_status('lost', month_start, api_key=api_key, domain=domain)
    print(f"  Won this week: {len(won_deals_week)} | Won this month: {len(won_deals_month)}")
    print(f"  Lost this week: {len(lost_deals_week)} | Lost this month: {len(lost_deals_month)}")
    time.sleep(API_DELAY)

    # 4. Fetch activities
    print("\nFetching activities...")
    activities_done_week = fetch_activities(
        api_key=api_key, domain=domain, start_date=week_start, done=True)
    time.sleep(API_DELAY)
    activities_overdue = fetch_activities(
        api_key=api_key, domain=domain, end_date=today_str, done=False)
    # Filter to only actually overdue (due_date < today)
    activities_overdue = [a for a in activities_overdue if (a.get('due_date') or '') < today_str]
    print(f"  Done this week: {len(activities_done_week)} | Overdue: {len(activities_overdue)}")

    # 4b. Fetch Allen's undone activities due today or earlier
    # (matches Pipedrive filter "8. ALLEN - ACTIVITY TODAY": assigned=Allen, due<=today, done=To do)
    allen_user = next((u for u in users if 'allen' in u['name'].lower()), None)
    allen_id = allen_user['id'] if allen_user else None
    todays_activities = []
    overdue_activities_allen = []
    if allen_id:
        time.sleep(API_DELAY)
        allen_undone = fetch_activities(
            api_key=api_key, domain=domain, user_id=allen_id, done=False)
        todays_activities = [a for a in allen_undone if a.get('due_date') == today_str]
        overdue_activities_allen = [a for a in allen_undone
                                    if a.get('due_date') and a['due_date'] < today_str]
        print(f"  Allen's activities today: {len(todays_activities)} (+{len(overdue_activities_allen)} overdue)")

    # 4c. Fetch yesterday's completed activities (for call counts)
    # Filter client-side by due_date since API date params filter by add_time
    yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    time.sleep(API_DELAY)
    all_done_recent = fetch_activities(
        api_key=api_key, domain=domain, done=True,
        start_date=(today - timedelta(days=3)).strftime('%Y-%m-%d'))
    activities_yesterday = [a for a in all_done_recent if a.get('due_date') == yesterday_str]
    yesterday_cold_calls = sum(
        1 for a in activities_yesterday
        if (a.get('type') or '').startswith(COLD_ACTIVITY_PREFIX))
    yesterday_total_calls = sum(
        1 for a in activities_yesterday
        if 'call' in (a.get('type') or '').lower() or (a.get('type') or '').startswith(COLD_ACTIVITY_PREFIX))
    print(f"  Yesterday: {yesterday_total_calls} calls ({yesterday_cold_calls} cold)")

    # 5. Run checks
    print("\nRunning checks...")
    follow_up_items = check_follow_ups(all_deals, today_str)
    overdue_items = check_overdue_activities(activities_overdue, today_str)
    stale_items = check_stale_deals(all_deals, today_str)

    # Combine and sort action items by priority
    all_action_items = follow_up_items + overdue_items + stale_items
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    all_action_items.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 3))

    # 5b. Enrich flagged items with person-level context
    print("\nEnriching with person context...")
    from deal_context import enrich_with_person_context
    enrich_with_person_context(all_action_items, api_key=api_key, domain=domain, today_str=today_str)

    print(f"  Follow-up needed: {len(follow_up_items)}")
    print(f"  Overdue activities: {len(overdue_items)}")
    print(f"  Stale deals: {len(stale_items)}")
    print(f"  Total action items: {len(all_action_items)}")

    # 6. Build summaries
    pipeline_summary = build_pipeline_summary(all_deals)
    team_scorecard = build_team_scorecard(users, activities_done_week, activities_overdue, all_deals)
    kpis = build_kpis(won_deals_week, lost_deals_week, won_deals_month, lost_deals_month,
                      activities_done_week, all_deals)

    # 7. Build user map for action items
    user_map = {u['id']: u['name'] for u in users}
    for item in all_action_items:
        item['owner_name'] = user_map.get(item.get('owner_id', 0), 'Unassigned')

    result = {
        'generated_at': today.isoformat(),
        'date': today_str,
        'week_start': week_start,
        'month_start': month_start,
        'kpis': kpis,
        'action_items': all_action_items,
        'pipeline_summary': pipeline_summary,
        'team_scorecard': team_scorecard,
        'users': users,
        'todays_activities': todays_activities,
        'overdue_activities_allen': overdue_activities_allen,
        'yesterday_cold_calls': yesterday_cold_calls,
        'yesterday_total_calls': yesterday_total_calls,
    }

    return result


def print_summary(result):
    """Print human-readable summary."""
    kpis = result['kpis']
    print("\n" + "=" * 60)
    print("  CRM MONITOR REPORT")
    print("=" * 60)

    print(f"\n--- TOP LINE KPIs ---")
    print(f"  Pipeline: {kpis['pipeline_deals']} deals | ${kpis['pipeline_value']:,.0f}")
    print(f"  Quotes in Sent: {kpis['quotes_in_sent']}")
    print(f"  Tenders active: {kpis['tenders_active']}")
    print(f"  Won this week: {kpis['deals_won_week']} (${kpis['won_value_week']:,.0f})")
    print(f"  Won this month: {kpis['deals_won_month']} (${kpis['won_value_month']:,.0f})")
    print(f"  Lost this month: {kpis['deals_lost_month']} (${kpis['lost_value_month']:,.0f})")
    print(f"  Conversion rate: {kpis['conversion_rate_month']}%")
    print(f"  Calls this week: {kpis['calls_this_week']}")
    print(f"  Emails this week: {kpis['emails_this_week']}")

    items = result['action_items']
    if items:
        print(f"\n--- ACTION ITEMS ({len(items)}) ---")
        for item in items:
            icon = {'URGENT': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '⚪'}.get(
                item['priority'], '⚪')
            if item['type'] == 'follow_up':
                action_text = {
                    'call_then_email': 'Call first → email if no answer',
                    'email': 'Send email nudge',
                    'urgent': 'URGENT — follow up immediately',
                }.get(item['recommended_action'], item['recommended_action'])
                print(f"\n  {icon} [{item['priority']}] FOLLOW UP: {item['deal_title']}")
                print(f"     Pipeline: {item['pipeline']} | Stage: {item['stage']}")
                print(f"     Owner: {item.get('owner_name', 'Unknown')}")
                print(f"     Last activity: {item['last_activity_date']} ({item['days_since_activity']} days ago)")
                if item['value']:
                    print(f"     Value: ${item['value']:,.0f} {item['currency']}")
                print(f"     → {action_text}")
            elif item['type'] == 'overdue_activity':
                print(f"\n  {icon} [{item['priority']}] OVERDUE: {item['subject']}")
                print(f"     Type: {item['activity_type']} | Due: {item['due_date']} ({item['days_overdue']} days overdue)")
                print(f"     Deal: {item.get('deal_title', 'N/A')}")
                print(f"     Owner: {item.get('owner_name', 'Unknown')}")
            elif item['type'] == 'stale_deal':
                print(f"\n  {icon} [{item['priority']}] STALE: {item['deal_title']}")
                print(f"     Pipeline: {item['pipeline']} | Stage: {item['stage']}")
                print(f"     Last activity: {item['last_activity_date']} ({item['days_since_activity']} days ago)")

    scorecard = result['team_scorecard']
    if scorecard:
        print(f"\n--- TEAM SCORECARD ---")
        print(f"  {'Name':<20} {'Calls':>6} {'Emails':>7} {'Deals':>6} {'Value':>12} {'Overdue':>8}")
        print(f"  {'-'*20} {'-'*6} {'-'*7} {'-'*6} {'-'*12} {'-'*8}")
        for name, card in scorecard.items():
            print(f"  {name:<20} {card['calls_this_week']:>6} {card['emails_this_week']:>7} "
                  f"{card['deals_in_pipeline']:>6} ${card['pipeline_value']:>10,.0f} "
                  f"{card['overdue_items']:>8}")

    pipeline = result['pipeline_summary']
    if pipeline:
        print(f"\n--- PIPELINE BREAKDOWN ---")
        for pname, pdata in pipeline.items():
            if pdata['total_deals'] == 0:
                continue
            print(f"\n  {pname}: {pdata['total_deals']} deals (${pdata['total_value']:,.0f})")
            for sname, sdata in pdata['stages'].items():
                print(f"    {sname}: {sdata['count']} deals (${sdata['value']:,.0f})")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description='CRM Monitor — scan Pipedrive pipelines')
    parser.add_argument('--print', action='store_true', help='Print human-readable summary')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no activities created')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN', '')

    if not api_key or not domain:
        print("ERROR: Missing PIPEDRIVE_API_KEY or PIPEDRIVE_COMPANY_DOMAIN in .env",
              file=sys.stderr)
        sys.exit(1)

    result = run_monitor(api_key=api_key, domain=domain, dry_run=args.dry_run,
                         verbose=args.verbose)

    # Save JSON output
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nJSON output saved to: {OUTPUT_FILE}")

    if args.print:
        print_summary(result)

    # Summary stats
    print(f"\n--- Summary ---")
    print(f"  Action items: {len(result['action_items'])}")
    urgent = sum(1 for i in result['action_items'] if i['priority'] == 'URGENT')
    high = sum(1 for i in result['action_items'] if i['priority'] == 'HIGH')
    if urgent:
        print(f"  URGENT: {urgent}")
    if high:
        print(f"  HIGH: {high}")


if __name__ == '__main__':
    main()
