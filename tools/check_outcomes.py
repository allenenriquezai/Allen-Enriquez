#!/usr/bin/env python3
"""
check_outcomes.py — EOD outcome checker.

Reads .tmp/outcome_log.jsonl, finds entries due for checking,
queries Pipedrive/Gmail for results, updates the log.

Runs daily chained after eod_ops_manager.py + crm_sync.py.
Zero LLM cost — pure API logic.

Usage:
    python3 tools/check_outcomes.py              # check all due
    python3 tools/check_outcomes.py --dry-run    # preview, no writes
    python3 tools/check_outcomes.py --print      # human-readable summary
    python3 tools/check_outcomes.py --domain eps # filter by domain
    python3 tools/check_outcomes.py --all        # check everything, not just due

Output:
    .tmp/outcome_log.jsonl      — updated with results
    .tmp/outcome_summary.json   — stats for /start dashboard
    .tmp/workflow_flags.json    — suggested workflow changes (phase 2)
"""

import argparse
import json
import os
import pickle
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / '.tmp' / 'outcome_log.jsonl'
SUMMARY_FILE = BASE_DIR / '.tmp' / 'outcome_summary.json'
FLAGS_FILE = BASE_DIR / '.tmp' / 'workflow_flags.json'
CONTENT_DUE_FILE = BASE_DIR / '.tmp' / 'content_outcomes_due.json'

# --- Pipedrive API (same pattern as eod_ops_manager.py) ---

EPS_ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
API_DELAY = 0.25


def load_env(env_file):
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


EPS_ENV = load_env(EPS_ENV_FILE)
PD_API_KEY = EPS_ENV.get('PIPEDRIVE_API_KEY', '')
PD_DOMAIN = EPS_ENV.get('PIPEDRIVE_COMPANY_DOMAIN', '')


def pd_get(path, params=None):
    if not PD_API_KEY or not PD_DOMAIN:
        return None
    params = params or {}
    params['api_token'] = PD_API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"https://{PD_DOMAIN}/api/v1{path}?{qs}"
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                return json.loads(r.read())
        return None


# --- Gmail API (same pattern as send_email_gmail.py) ---

EPS_TOKEN = BASE_DIR / 'projects' / 'eps' / 'token_eps.pickle'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'


def get_gmail_service(domain):
    token_file = EPS_TOKEN if domain == 'eps' else PERSONAL_TOKEN
    if not token_file.exists():
        return None
    try:
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        return None
    with open(token_file, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)


# --- Log I/O ---

def load_log():
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def save_log(entries):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')


# --- Checker functions ---

def check_deal_stage(entry):
    """Check if Pipedrive deal stage changed since the action was logged."""
    ref = entry.get('ref', '')
    if not ref.startswith('deal:'):
        return None

    deal_id = ref.split(':')[1]
    if deal_id == 'test':
        return {'result': 'no_change', 'result_detail': 'Test entry — skipped'}

    data = pd_get(f'/deals/{deal_id}')
    if not data or not data.get('data'):
        return {'result': 'no_change', 'result_detail': 'Deal not found or API error'}

    deal = data['data']
    status = deal.get('status', 'open')
    stage_name = deal.get('stage_id')  # numeric, but we can compare

    if status == 'won':
        return {
            'result': 'won',
            'result_detail': f"Deal WON — {deal.get('title', '')}",
        }
    elif status == 'lost':
        lost_reason = deal.get('lost_reason', 'No reason given')
        return {
            'result': 'lost',
            'result_detail': f"Deal LOST — {lost_reason}",
        }

    # Check if stage changed by comparing update_time vs log time
    log_ts = entry.get('ts', '')[:10]
    update_time = (deal.get('stage_change_time') or '')[:10]
    if update_time and update_time > log_ts:
        return {
            'result': 'stage_changed',
            'result_detail': f"Stage changed after action (updated {update_time})",
        }

    return None  # No result yet — keep checking


def check_email_reply(entry):
    """Check Gmail for replies to an email we sent."""
    service = get_gmail_service(entry.get('domain', 'eps'))
    if not service:
        return None

    # Get the contact email from the detail or ref
    ref = entry.get('ref', '')
    detail = entry.get('detail', '')

    # If ref has deal ID, get contact email from Pipedrive
    contact_email = None
    if ref.startswith('deal:'):
        deal_id = ref.split(':')[1]
        if deal_id != 'test':
            data = pd_get(f'/deals/{deal_id}')
            if data and data.get('data'):
                person_id = data['data'].get('person_id', {})
                if isinstance(person_id, dict):
                    pid = person_id.get('value')
                elif person_id:
                    pid = person_id
                else:
                    pid = None
                if pid:
                    pdata = pd_get(f'/persons/{pid}')
                    if pdata and pdata.get('data'):
                        emails = pdata['data'].get('email', [])
                        if emails:
                            contact_email = emails[0].get('value', '')

    if not contact_email:
        return None  # Can't check without email

    # Search Gmail for replies from this contact after send date
    log_date = entry.get('ts', '')[:10]
    query = f"from:{contact_email} after:{log_date}"
    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=5
        ).execute()
        messages = results.get('messages', [])
        if messages:
            return {
                'result': 'replied',
                'result_detail': f"Reply from {contact_email} ({len(messages)} message(s))",
            }
    except Exception:
        return None  # API error, try again next run

    return None  # No reply yet


def check_content_manual(entry):
    """No API — queue for manual entry."""
    # Write to content_outcomes_due for /start to surface
    due = []
    if CONTENT_DUE_FILE.exists():
        due = json.loads(CONTENT_DUE_FILE.read_text())
    if not any(d['id'] == entry['id'] for d in due):
        due.append({
            'id': entry['id'],
            'detail': entry.get('detail', ''),
            'posted_date': entry.get('ts', '')[:10],
            'check_date': entry.get('check_date', ''),
        })
        CONTENT_DUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTENT_DUE_FILE, 'w') as f:
            json.dump(due, f, indent=2)
    return None  # Always manual


def check_outreach_log(entry):
    """Cross-reference outreach_log.jsonl for reply status."""
    log_path = BASE_DIR / 'projects' / 'personal' / '.tmp' / 'outreach_log.jsonl'
    if not log_path.exists():
        return None
    log_date = entry.get('ts', '')[:10]
    detail_lower = entry.get('detail', '').lower()
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        ol = json.loads(line)
        if ol.get('status') == 'replied' and ol.get('date', '') >= log_date:
            if detail_lower in (ol.get('prospect', '') or '').lower():
                return {
                    'result': 'replied',
                    'result_detail': f"Reply found in outreach log",
                }
    return None


# Action → checker mapping
CHECKERS = {
    'email_sent': check_email_reply,
    'quote_sent': check_deal_stage,
    'site_visit_done': check_deal_stage,
    'reengage_sent': check_email_reply,
    'content_posted': check_content_manual,
    'outreach_dm': check_outreach_log,
    'cold_call': check_deal_stage,
}


# --- Summary + Pattern Detection ---

def build_summary(entries):
    """Build outcome_summary.json for the /start dashboard."""
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d')

    recent = [e for e in entries if e.get('ts', '')[:10] >= thirty_days_ago]
    with_result = [e for e in recent if e.get('result') is not None]
    pending = [e for e in recent if e.get('result') is None]

    by_action = defaultdict(lambda: defaultdict(int))
    for e in recent:
        action = e['action']
        result = e.get('result') or 'pending'
        by_action[action][result] += 1
        by_action[action]['total'] += 1

    # Calculate rates
    action_stats = {}
    for action, counts in by_action.items():
        total = counts['total']
        stats = dict(counts)
        if action in ('email_sent', 'reengage_sent', 'outreach_dm'):
            replied = counts.get('replied', 0)
            checked = total - counts.get('pending', 0)
            stats['reply_rate'] = round(replied / checked, 2) if checked > 0 else None
        elif action in ('quote_sent',):
            won = counts.get('won', 0)
            checked = total - counts.get('pending', 0)
            stats['win_rate'] = round(won / checked, 2) if checked > 0 else None
        action_stats[action] = stats

    summary = {
        'timestamp': now.isoformat(timespec='seconds'),
        'total_tracked': len(recent),
        'results_back': len(with_result),
        'pending_check': len(pending),
        'by_action': action_stats,
    }

    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_FILE, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def print_summary(summary):
    print(f"\n{'=' * 50}")
    print(f"  OUTCOME TRACKING SUMMARY")
    print(f"{'=' * 50}")
    print(f"  Total tracked (30d): {summary['total_tracked']}")
    print(f"  Results back:        {summary['results_back']}")
    print(f"  Pending check:       {summary['pending_check']}")
    print()

    for action, stats in summary.get('by_action', {}).items():
        total = stats.get('total', 0)
        line = f"  {action:20s} total={total}"
        if 'reply_rate' in stats and stats['reply_rate'] is not None:
            line += f"  reply_rate={stats['reply_rate']:.0%}"
        if 'win_rate' in stats and stats['win_rate'] is not None:
            line += f"  win_rate={stats['win_rate']:.0%}"
        print(line)

    print(f"{'=' * 50}\n")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='EOD outcome checker')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no file writes')
    parser.add_argument('--print', dest='do_print', action='store_true', help='Human-readable summary')
    parser.add_argument('--domain', default=None, choices=['eps', 'personal'])
    parser.add_argument('--all', action='store_true', help='Check all entries, not just due')
    args = parser.parse_args()

    entries = load_log()
    if not entries:
        if args.do_print:
            print("No outcomes logged yet.")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    checked = 0
    results_found = 0

    for entry in entries:
        # Skip already resolved
        if entry.get('result') is not None:
            continue

        # Filter by domain
        if args.domain and entry.get('domain') != args.domain:
            continue

        # Skip if not yet due (unless --all)
        if not args.all and entry.get('check_date', '') > today:
            continue

        checker = CHECKERS.get(entry['action'])
        if not checker:
            continue

        checked += 1
        result = checker(entry)

        if result:
            results_found += 1
            if not args.dry_run:
                entry['result'] = result['result']
                entry['result_ts'] = datetime.now().isoformat(timespec='seconds')
                entry['result_detail'] = result.get('result_detail', '')

            if args.do_print:
                print(f"  [{result['result']:15s}] {entry['detail'][:50]} — {result.get('result_detail', '')}")

        time.sleep(API_DELAY)

    if not args.dry_run:
        save_log(entries)
        summary = build_summary(entries)
    else:
        summary = build_summary(entries)

    if args.do_print:
        print(f"\n  Checked: {checked} | Results found: {results_found}")
        print_summary(summary)

    # Always write summary (even on dry-run, it's read-only stats)
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_FILE, 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
