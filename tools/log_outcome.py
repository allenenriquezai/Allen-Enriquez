#!/usr/bin/env python3
"""
log_outcome.py — Log an outbound action for outcome tracking.

Appends to .tmp/outcome_log.jsonl. The EOD checker (check_outcomes.py)
reads this log and checks whether each action got a result.

Usage:
    python3 tools/log_outcome.py \
        --action email_sent \
        --domain eps \
        --ref "deal:1302" \
        --detail "Quote follow-up to Mother Duck" \
        --check-days 3 \
        --tags follow-up,quote-sent \
        --template quote-followup-v2

    python3 tools/log_outcome.py \
        --action content_posted \
        --domain personal \
        --detail "4 Levels of AI reel" \
        --check-days 7

    python3 tools/log_outcome.py list                    # show recent entries
    python3 tools/log_outcome.py list --pending          # show unchecked only
    python3 tools/log_outcome.py list --domain eps       # filter by domain

Actions: email_sent, quote_sent, content_posted, site_visit_done,
         reengage_sent, outreach_dm, cold_call
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / '.tmp' / 'outcome_log.jsonl'

VALID_ACTIONS = [
    'email_sent', 'quote_sent', 'content_posted', 'site_visit_done',
    'reengage_sent', 'outreach_dm', 'cold_call',
]

DEFAULT_CHECK_DAYS = {
    'email_sent': 3,
    'quote_sent': 7,
    'content_posted': 7,
    'site_visit_done': 5,
    'reengage_sent': 3,
    'outreach_dm': 3,
    'cold_call': 2,
}


def generate_id():
    import random
    date_part = datetime.now().strftime('%Y%m%d')
    hex_part = ''.join(random.choices('0123456789abcdef', k=4))
    return f"out_{date_part}_{hex_part}"


def log_outcome(action, domain, ref, detail, check_days, tags, template):
    if action not in VALID_ACTIONS:
        print(f"Invalid action: {action}. Valid: {', '.join(VALID_ACTIONS)}")
        sys.exit(1)

    if check_days is None:
        check_days = DEFAULT_CHECK_DAYS.get(action, 3)

    entry = {
        'id': generate_id(),
        'ts': datetime.now().isoformat(timespec='seconds'),
        'action': action,
        'domain': domain or 'eps',
        'ref': ref or '',
        'detail': detail,
        'check_date': (datetime.now() + timedelta(days=check_days)).strftime('%Y-%m-%d'),
        'tags': [t.strip() for t in tags.split(',')] if tags else [],
        'template': template or '',
        'result': None,
        'result_ts': None,
        'result_detail': None,
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    print(f"Logged: {action} | {detail} | check by {entry['check_date']}")
    return entry


def load_log():
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def list_entries(domain=None, pending=False, limit=20):
    entries = load_log()
    if domain:
        entries = [e for e in entries if e['domain'] == domain]
    if pending:
        entries = [e for e in entries if e.get('result') is None]

    entries = entries[-limit:]

    if not entries:
        print("No entries found.")
        return

    for e in entries:
        status = e.get('result') or 'pending'
        marker = '.' if status == 'pending' else ('*' if status in ('replied', 'won', 'stage_changed') else 'x')
        print(f"  [{marker}] {e['ts'][:10]} {e['action']:16s} {e['detail'][:50]:50s} → {status}")

    total = len(load_log())
    shown = len(entries)
    print(f"\n  Showing {shown} of {total} entries")


def main():
    parser = argparse.ArgumentParser(description='Log an outbound action for outcome tracking')
    sub = parser.add_subparsers(dest='command')

    # Default: log an outcome
    log_parser = sub.add_parser('log', help='Log a new outcome (default)')
    log_parser.add_argument('--action', required=True, choices=VALID_ACTIONS)
    log_parser.add_argument('--domain', default='eps', choices=['eps', 'personal'])
    log_parser.add_argument('--ref', default='', help='Reference (e.g. deal:1302)')
    log_parser.add_argument('--detail', required=True, help='What was done')
    log_parser.add_argument('--check-days', type=int, default=None, help='Days until result check')
    log_parser.add_argument('--tags', default='', help='Comma-separated tags')
    log_parser.add_argument('--template', default='', help='Template/variant used')

    # List entries
    list_parser = sub.add_parser('list', help='Show recent entries')
    list_parser.add_argument('--domain', default=None, choices=['eps', 'personal'])
    list_parser.add_argument('--pending', action='store_true', help='Show only unchecked')
    list_parser.add_argument('--limit', type=int, default=20)

    args = parser.parse_args()

    # Default to log if --action provided without subcommand
    if args.command is None:
        # Check if bare args look like a log command
        if any(a in sys.argv for a in ['--action']):
            # Re-parse as log
            args = log_parser.parse_args(sys.argv[1:])
            args.command = 'log'
        else:
            parser.print_help()
            return

    if args.command == 'log':
        log_outcome(args.action, args.domain, args.ref, args.detail,
                    args.check_days, args.tags, args.template)
    elif args.command == 'list':
        list_entries(args.domain, args.pending, args.limit)


if __name__ == '__main__':
    main()
