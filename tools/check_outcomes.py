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

INTEL_DIR = BASE_DIR / 'projects' / 'personal' / 'reference' / 'intel'

# Min data points before a pattern is flagged
MIN_PATTERN_DATA = 5
# Min ratio difference to flag (e.g., 1.5 = 50% better)
MIN_PATTERN_RATIO = 1.5


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


# --- Pattern Detection ---

def detect_patterns(entries, dry_run=False):
    """Analyze resolved outcomes for patterns. Returns list of detected patterns."""
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d')

    resolved = [
        e for e in entries
        if e.get('result') is not None and e.get('ts', '')[:10] >= thirty_days_ago
    ]

    if len(resolved) < MIN_PATTERN_DATA:
        return []

    patterns = []
    patterns.extend(_detect_template_patterns(resolved))
    patterns.extend(_detect_tag_patterns(resolved))
    patterns.extend(_detect_domain_patterns(resolved))

    if not dry_run:
        _update_intel_docs(patterns)
        _update_workflow_flags(patterns)

    return patterns


def _detect_template_patterns(entries):
    """Compare reply/win rates across templates within same action type."""
    patterns = []

    # Group by (action, template)
    by_template = defaultdict(list)
    for e in entries:
        tmpl = e.get('template', '').strip()
        if tmpl:
            by_template[(e['action'], tmpl)].append(e)

    # Group by action for overall average
    by_action = defaultdict(list)
    for e in entries:
        by_action[e['action']].append(e)

    for (action, template), group in by_template.items():
        if len(group) < MIN_PATTERN_DATA:
            continue

        rate, rate_type = _calc_rate(group, action)
        if rate is None:
            continue

        avg_rate, _ = _calc_rate(by_action[action], action)
        if avg_rate is None or avg_rate == 0:
            continue

        ratio = rate / avg_rate if avg_rate > 0 else 0

        if ratio >= MIN_PATTERN_RATIO:
            patterns.append({
                'type': 'template_winner',
                'action': action,
                'template': template,
                'rate': rate,
                'rate_type': rate_type,
                'avg_rate': avg_rate,
                'ratio': round(ratio, 1),
                'n': len(group),
                'description': f"Template '{template}' gets {ratio:.1f}x {rate_type} ({rate:.0%} vs {avg_rate:.0%} avg, n={len(group)})",
            })
        elif ratio <= (1 / MIN_PATTERN_RATIO) and len(group) >= MIN_PATTERN_DATA:
            patterns.append({
                'type': 'template_loser',
                'action': action,
                'template': template,
                'rate': rate,
                'rate_type': rate_type,
                'avg_rate': avg_rate,
                'ratio': round(ratio, 1),
                'n': len(group),
                'description': f"Template '{template}' underperforms — {rate:.0%} {rate_type} vs {avg_rate:.0%} avg (n={len(group)})",
            })

    return patterns


def _detect_tag_patterns(entries):
    """Compare rates across tags (e.g., follow-up vs cold-outreach)."""
    patterns = []

    # Explode tags
    by_tag = defaultdict(list)
    for e in entries:
        for tag in e.get('tags', []):
            by_tag[(e['action'], tag)].append(e)

    by_action = defaultdict(list)
    for e in entries:
        by_action[e['action']].append(e)

    for (action, tag), group in by_tag.items():
        if len(group) < MIN_PATTERN_DATA:
            continue

        rate, rate_type = _calc_rate(group, action)
        if rate is None:
            continue

        avg_rate, _ = _calc_rate(by_action[action], action)
        if avg_rate is None or avg_rate == 0:
            continue

        ratio = rate / avg_rate if avg_rate > 0 else 0

        if ratio >= MIN_PATTERN_RATIO:
            patterns.append({
                'type': 'tag_winner',
                'action': action,
                'tag': tag,
                'rate': rate,
                'rate_type': rate_type,
                'avg_rate': avg_rate,
                'ratio': round(ratio, 1),
                'n': len(group),
                'description': f"Tag '{tag}' gets {ratio:.1f}x {rate_type} ({rate:.0%} vs {avg_rate:.0%} avg, n={len(group)})",
            })

    return patterns


def _detect_domain_patterns(entries):
    """Compare rates across EPS vs personal domain."""
    patterns = []

    by_domain = defaultdict(list)
    for e in entries:
        by_domain[e.get('domain', 'eps')].append(e)

    if len(by_domain) < 2:
        return patterns

    for action in set(e['action'] for e in entries):
        domain_rates = {}
        for domain, group in by_domain.items():
            action_group = [e for e in group if e['action'] == action]
            if len(action_group) < MIN_PATTERN_DATA:
                continue
            rate, rate_type = _calc_rate(action_group, action)
            if rate is not None:
                domain_rates[domain] = (rate, rate_type, len(action_group))

        if len(domain_rates) == 2:
            domains = list(domain_rates.keys())
            r0, rt, n0 = domain_rates[domains[0]]
            r1, _, n1 = domain_rates[domains[1]]
            if r1 > 0 and r0 / r1 >= MIN_PATTERN_RATIO:
                patterns.append({
                    'type': 'domain_diff',
                    'action': action,
                    'rate_type': rt,
                    'description': f"{action} {rt}: {domains[0]} ({r0:.0%}, n={n0}) vs {domains[1]} ({r1:.0%}, n={n1})",
                })

    return patterns


def _calc_rate(entries, action):
    """Calculate the relevant rate for an action type."""
    if action in ('email_sent', 'reengage_sent', 'outreach_dm'):
        replied = sum(1 for e in entries if e.get('result') == 'replied')
        total = len(entries)
        return (replied / total if total > 0 else None, 'reply_rate')
    elif action in ('quote_sent',):
        won = sum(1 for e in entries if e.get('result') == 'won')
        total = len(entries)
        return (won / total if total > 0 else None, 'win_rate')
    elif action in ('content_posted',):
        # Content doesn't have a binary rate — skip for now
        return (None, None)
    return (None, None)


# --- Intel Doc Auto-Append ---

def _update_intel_docs(patterns):
    """Append pattern findings to relevant intel docs."""
    today = datetime.now().strftime('%Y-%m-%d')

    for p in patterns:
        action = p.get('action', '')
        ptype = p.get('type', '')

        if action in ('email_sent', 'reengage_sent', 'outreach_dm'):
            _append_to_intel('outreach-whats-working.md', p, today)
        elif action == 'quote_sent':
            _append_to_intel('performance-scorecard.md', p, today)
        elif action == 'content_posted':
            _append_to_intel('content-whats-working.md', p, today)


def _append_to_intel(filename, pattern, today):
    """Append a pattern finding to an intel doc."""
    filepath = INTEL_DIR / filename
    if not filepath.exists():
        return

    content = filepath.read_text()

    # Build the entry line
    desc = pattern['description']
    entry = f"| {today} | {desc} | outcome_tracker |\n"

    # Determine target section based on pattern type and action
    target_section = _get_target_section(filename, pattern)
    if not target_section:
        return

    # Check for duplicate (same description already in file)
    if desc in content:
        return

    # Find the section and append after the table header or placeholder
    lines = content.split('\n')
    new_lines = []
    inserted = False

    for i, line in enumerate(lines):
        new_lines.append(line)
        if not inserted and target_section.lower() in line.lower():
            # Find the end of the table header (look for |---|)
            for j in range(i + 1, min(i + 5, len(lines))):
                if '|---|' in lines[j] or '(populate' in lines[j].lower():
                    # Insert after separator row, or replace placeholder
                    if '(populate' in lines[j].lower():
                        # Replace placeholder with actual data
                        new_lines.append(f"| Date | Finding | Source |")
                        new_lines.append(f"|---|---|---|")
                        new_lines.append(entry.rstrip())
                        # Skip the placeholder line
                        lines[j] = ''
                    break
            else:
                # No table found — append as bullet
                new_lines.append(f"- **{today}**: {desc} (outcome_tracker)")
            inserted = True

    if inserted:
        result = '\n'.join(new_lines)
        # Update the last_updated header
        result = _update_last_updated(result, today)
        filepath.write_text(result)


def _get_target_section(filename, pattern):
    """Map pattern to the correct section in an intel doc."""
    ptype = pattern.get('type', '')
    action = pattern.get('action', '')

    if filename == 'outreach-whats-working.md':
        if 'template' in ptype:
            return 'DM Templates'
        if 'tag' in ptype:
            return 'Best Openers'
        return 'DM Templates'

    elif filename == 'performance-scorecard.md':
        return 'Sales Pipeline'

    elif filename == 'content-whats-working.md':
        if 'winner' in ptype:
            return 'Best Performing Hooks'
        if 'loser' in ptype:
            return 'Hooks That Flopped'
        return 'Best Performing Hooks'

    return None


def _update_last_updated(content, today):
    """Update the > Last updated: line in an intel doc."""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('> Last updated:'):
            lines[i] = f'> Last updated: {today}'
        elif line.startswith('> Updated by:'):
            lines[i] = f'> Updated by: outcome_tracker (automated)'
    return '\n'.join(lines)


# --- Workflow Flags ---

def _update_workflow_flags(patterns):
    """Write strong patterns as workflow update suggestions."""
    import hashlib

    existing = []
    if FLAGS_FILE.exists():
        existing = json.loads(FLAGS_FILE.read_text())

    existing_hashes = {f.get('pattern_hash') for f in existing}
    today = datetime.now().strftime('%Y-%m-%d')

    for p in patterns:
        # Only flag winners with enough data
        if 'winner' not in p.get('type', '') and 'diff' not in p.get('type', ''):
            continue
        if p.get('n', 0) < MIN_PATTERN_DATA:
            continue

        # Generate hash to avoid duplicates
        hash_input = f"{p['action']}:{p.get('template', '')}:{p.get('tag', '')}:{p['description']}"
        pattern_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        if pattern_hash in existing_hashes:
            continue

        target_file = _suggest_target_file(p)

        existing.append({
            'id': f"wf_{today.replace('-', '')}_{pattern_hash[:4]}",
            'created': today,
            'domain': p.get('domain', 'eps'),
            'pattern': p['description'],
            'suggestion': _suggest_action(p),
            'target_file': target_file,
            'data_points': p.get('n', 0),
            'status': 'pending',
            'pattern_hash': pattern_hash,
        })

    FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FLAGS_FILE, 'w') as f:
        json.dump(existing, f, indent=2)


def _suggest_target_file(pattern):
    """Suggest which workflow file should be updated."""
    action = pattern.get('action', '')
    if action in ('email_sent', 'reengage_sent'):
        return 'projects/eps/workflows/sales/follow-up-email.md'
    elif action == 'outreach_dm':
        return 'projects/personal/workflows/sales/outreach.md'
    elif action == 'quote_sent':
        return 'projects/eps/workflows/sales/create-quote.md'
    elif action == 'content_posted':
        return 'projects/personal/workflows/content/content-creation.md'
    elif action == 'cold_call':
        return 'projects/eps/workflows/lead-gen/cold-calling.md'
    return ''


def _suggest_action(pattern):
    """Generate a human-readable suggestion for what to change."""
    ptype = pattern.get('type', '')
    if ptype == 'template_winner':
        return f"Default to template '{pattern.get('template', '')}' — it outperforms alternatives"
    elif ptype == 'tag_winner':
        return f"Prioritize '{pattern.get('tag', '')}' approach — higher conversion"
    elif ptype == 'domain_diff':
        return f"Review {pattern.get('action', '')} approach — domains performing differently"
    return f"Review based on pattern: {pattern.get('description', '')}"


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

    # Pattern detection — runs on all resolved entries
    patterns = detect_patterns(entries, dry_run=args.dry_run)

    if args.do_print:
        print(f"\n  Checked: {checked} | Results found: {results_found}")
        print_summary(summary)
        if patterns:
            print(f"  PATTERNS DETECTED: {len(patterns)}")
            for p in patterns:
                print(f"    → {p['description']}")
            print()
        else:
            print(f"  Patterns: none yet (need {MIN_PATTERN_DATA}+ data points per group)")
            print()


if __name__ == '__main__':
    main()
