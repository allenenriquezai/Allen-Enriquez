"""
Ryan labeler — weekly self-improvement

Analyzes local audit log, finds recurring sender patterns, auto-adds learned
routing rules to routing_rules.json, redeploys Railway, emails a report.

Usage:
    python3 tools/shared/ryan_self_improve.py              # full run
    python3 tools/shared/ryan_self_improve.py --dry-run    # preview, no changes
    python3 tools/shared/ryan_self_improve.py --force      # skip min-data guards

Scheduled via launchd: Sunday 08:00 AM.

Auto-applies:
  - New sender_hints entries where a domain appears 5+ times, same bucket, avg
    confidence >= 0.85, and the domain is NOT already in routing_rules.json.

Emails for review (does NOT auto-apply):
  - Classifier prompt improvement suggestions derived from low-confidence patterns.
  - Sender rules that pass the 3-hit threshold but not the 5-hit / 0.85 threshold.
"""

import argparse
import base64
import json
import os
import pickle
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
SHARED_ENV = BASE_DIR / 'projects' / '.env'
PERSONAL_ENV = BASE_DIR / 'projects' / 'personal' / '.env'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
LOCAL_AUDIT_FILE = BASE_DIR / '.tmp' / 'ryan_audit_local.jsonl'
ROUTING_RULES_FILE = BASE_DIR / 'services' / 'ryan' / 'config' / 'routing_rules.json'
SERVICE_CODE_DIR = BASE_DIR / 'services' / 'ryan'
RAILWAY_CLI = '/opt/homebrew/bin/railway'
RAILWAY_PROJECT = 'enriquez-os'
RAILWAY_SERVICE = 'ryan-labeler'
RAILWAY_ENV_NAME = 'production'

ALERT_TO = 'allenenriquez.ai@gmail.com'
FROM_EMAIL = 'allenenriquez.ai@gmail.com'
FROM_NAME = 'Enriquez OS'

AUTO_APPLY_MIN_HITS = 5
AUTO_APPLY_MIN_CONFIDENCE = 0.85
SUGGEST_MIN_HITS = 3


def load_env():
    for env_file in [SHARED_ENV, PERSONAL_ENV]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------

def send_email(subject, body):
    if not PERSONAL_TOKEN.exists():
        print(f'ERROR: token missing — {PERSONAL_TOKEN}', file=sys.stderr)
        return False
    with open(PERSONAL_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(PERSONAL_TOKEN, 'wb') as f:
            pickle.dump(creds, f)
    svc = build('gmail', 'v1', credentials=creds)
    msg = MIMEText(body, 'plain')
    msg['to'] = ALERT_TO
    msg['from'] = f'{FROM_NAME} <{FROM_EMAIL}>'
    msg['subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId='me', body={'raw': raw}).execute()
    return True


# ---------------------------------------------------------------------------
# Audit analysis
# ---------------------------------------------------------------------------

def load_audit():
    if not LOCAL_AUDIT_FILE.exists():
        return []
    entries = []
    for line in LOCAL_AUDIT_FILE.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def extract_sender_domain(from_addr):
    """'John Doe <john@example.com>' → 'example.com'"""
    if not from_addr:
        return None
    addr = from_addr
    if '<' in addr:
        addr = addr.split('<')[1].rstrip('>')
    if '@' in addr:
        return addr.split('@')[1].lower().strip()
    return None


def analyze_sender_patterns(entries):
    """
    Returns two dicts:
      auto_apply: {domain: {bucket, hits, avg_confidence}} — safe to auto-add
      suggestions: {domain: {bucket, hits, avg_confidence}} — needs review
    """
    # {domain: {bucket: [confidence, ...]}}
    domain_buckets = defaultdict(lambda: defaultdict(list))

    for e in entries:
        classification = e.get('classification', {})
        bucket = classification.get('category')
        confidence = classification.get('confidence', 0)
        from_addr = e.get('from', '')
        domain = extract_sender_domain(from_addr)

        if not domain or not bucket or bucket in ('skip', 'other', 'personal'):
            continue

        domain_buckets[domain][bucket].append(confidence)

    auto_apply = {}
    suggestions = {}

    for domain, buckets in domain_buckets.items():
        # Find the dominant bucket for this domain
        dominant = max(buckets.items(), key=lambda kv: len(kv[1]))
        bucket, confidences = dominant
        hits = len(confidences)
        avg_conf = sum(confidences) / hits if confidences else 0

        # Only consider domains where 80%+ of emails go to the same bucket
        total_hits = sum(len(v) for v in buckets.values())
        consistency = hits / total_hits if total_hits else 0
        if consistency < 0.8:
            continue

        record = {'bucket': bucket, 'hits': hits, 'avg_confidence': round(avg_conf, 3), 'consistency': round(consistency, 3)}

        if hits >= AUTO_APPLY_MIN_HITS and avg_conf >= AUTO_APPLY_MIN_CONFIDENCE:
            auto_apply[domain] = record
        elif hits >= SUGGEST_MIN_HITS:
            suggestions[domain] = record

    return auto_apply, suggestions


def load_existing_hint_domains():
    """Return set of domains already covered by sender_hints in routing_rules.json."""
    rules = json.loads(ROUTING_RULES_FILE.read_text())
    covered = set()
    for hint in rules.get('sender_hints', {}).get('rules', []):
        domain = hint.get('match_from_domain', '')
        if domain:
            covered.add(domain.lower())
        # Also parse comma-separated domain lists
        multi = hint.get('match_from_domain_contains', '')
        if multi:
            for d in multi.split(','):
                covered.add(d.strip().lower())
    # Also cover explicit sender overrides
    for rule in rules.get('sender_overrides', {}).get('rules', []):
        for addr in rule.get('match_from_contains', []):
            if '@' in addr:
                covered.add(addr.split('@')[1].lower())
    return covered


def apply_routing_rules(new_hints):
    """Add new entries to sender_hints.rules in routing_rules.json. Returns count added."""
    rules = json.loads(ROUTING_RULES_FILE.read_text())
    hint_rules = rules.setdefault('sender_hints', {}).setdefault('rules', [])

    added = 0
    for domain, info in new_hints.items():
        hint_rules.append({
            'match_from_domain': domain,
            'force_bucket': info['bucket'],
            'note': f'Auto-learned: {info["hits"]} emails, avg confidence {info["avg_confidence"]}, added {datetime.now(timezone.utc).strftime("%Y-%m-%d")}',
        })
        added += 1

    ROUTING_RULES_FILE.write_text(json.dumps(rules, indent=2))
    return added


def redeploy_railway():
    """Link + deploy Railway. Returns (ok, log)."""
    steps = []

    def run(cmd, timeout=60):
        r = subprocess.run(
            cmd, cwd=str(SERVICE_CODE_DIR), capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0, r.stdout.strip() or r.stderr.strip()

    ok, out = run([RAILWAY_CLI, 'link', '-p', RAILWAY_PROJECT, '-s', RAILWAY_SERVICE, '-e', RAILWAY_ENV_NAME])
    steps.append(f'link: {"ok" if ok else out}')
    if not ok:
        return False, '\n'.join(steps)

    ok, out = run([RAILWAY_CLI, 'up', '--detach'], timeout=120)
    steps.append(f'deploy: {"triggered" if ok else out}')
    return ok, '\n'.join(steps)


# ---------------------------------------------------------------------------
# Claude prompt improvement suggestions
# ---------------------------------------------------------------------------

def suggest_prompt_improvements(low_confidence_entries):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key or len(low_confidence_entries) < 5:
        return None

    sample = low_confidence_entries[:20]
    sample_text = '\n'.join(
        f'- from={e.get("from", "")[:60]} subject={e.get("classification", {}).get("reason", "")[:80]} → {e.get("classification", {}).get("category")} ({e.get("classification", {}).get("confidence")})'
        for e in sample
    )

    prompt = (
        'You are reviewing an email classifier for a construction contractor\'s inbox.\n'
        'These emails were classified with low confidence (< 0.7) or landed in "other".\n'
        'Identify 1-3 concrete additions or clarifications to the classifier prompt that would fix these.\n'
        'Be specific. Output as a numbered list only.\n\n'
        f'Low-confidence examples:\n{sample_text}'
    )

    payload = json.dumps({
        'model': 'claude-sonnet-4-6',
        'max_tokens': 400,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=payload,
        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())['content'][0]['text']
    except Exception as e:
        return f'(Claude unavailable: {e})'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true', help='Skip min-data guards')
    args = parser.parse_args()

    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'[{ts}] ryan self-improve')

    entries = load_audit()
    print(f'  Audit entries: {len(entries)}')

    if len(entries) < 10 and not args.force:
        print('  Not enough data yet (need 10+). Run with --force to override.')
        return

    # Analyse patterns
    auto_apply, suggestions = analyze_sender_patterns(entries)
    existing_domains = load_existing_hint_domains()

    # Filter out already-covered domains
    new_auto = {d: v for d, v in auto_apply.items() if d not in existing_domains}
    new_suggestions = {d: v for d, v in suggestions.items() if d not in existing_domains and d not in new_auto}

    # Low-confidence entries for prompt improvement
    low_conf = [
        e for e in entries
        if e.get('classification', {}).get('confidence', 1) < 0.7
        or e.get('classification', {}).get('category') == 'other'
    ]

    print(f'  New auto-apply rules: {len(new_auto)}')
    print(f'  New suggestions: {len(new_suggestions)}')
    print(f'  Low-confidence emails: {len(low_conf)}')

    # ------------------------------------------------------------------
    # Auto-apply
    # ------------------------------------------------------------------
    deploy_needed = False
    applied_count = 0

    if new_auto and not args.dry_run:
        applied_count = apply_routing_rules(new_auto)
        deploy_needed = applied_count > 0
        print(f'  Applied {applied_count} new routing rules')
    elif new_auto and args.dry_run:
        print('  DRY RUN — would apply:')
        for d, v in new_auto.items():
            print(f'    {d} → {v["bucket"]} ({v["hits"]} hits, conf {v["avg_confidence"]})')

    if deploy_needed:
        print('  Redeploying Railway with updated rules...')
        ok, log = redeploy_railway()
        print(f'  Deploy: {"triggered" if ok else "FAILED — " + log}')

    # ------------------------------------------------------------------
    # Build report email
    # ------------------------------------------------------------------
    prompt_suggestions = suggest_prompt_improvements(low_conf)

    lines = [
        f'Ryan labeler weekly self-improve — {ts}',
        f'Audit entries analyzed: {len(entries)}',
        '',
    ]

    if new_auto:
        lines.append('AUTO-APPLIED routing rules:')
        for d, v in new_auto.items():
            status = '(applied + redeployed)' if not args.dry_run else '(dry-run)'
            lines.append(f'  {d} → {v["bucket"]}  [{v["hits"]} emails, conf {v["avg_confidence"]}] {status}')
        lines.append('')

    if new_suggestions:
        lines.append('SUGGESTED routing rules (not applied — below threshold):')
        for d, v in new_suggestions.items():
            lines.append(f'  {d} → {v["bucket"]}  [{v["hits"]} emails, conf {v["avg_confidence"]}]')
        lines.append('  → Reply or re-run with adjusted thresholds to apply.')
        lines.append('')

    if prompt_suggestions:
        lines.append('CLASSIFIER PROMPT suggestions (review before applying):')
        lines.append(prompt_suggestions)
        lines.append('')
        lines.append(f'  To apply: edit services/ryan/config/classifier_prompt.md then run: cd services/ryan && railway up --detach')
        lines.append('')

    if not new_auto and not new_suggestions and not prompt_suggestions:
        lines.append('No improvements found this week. System is well-calibrated.')

    lines += [
        '─' * 40,
        f'Auto-apply threshold: {AUTO_APPLY_MIN_HITS}+ hits, {AUTO_APPLY_MIN_CONFIDENCE} avg confidence',
        f'Suggestion threshold: {SUGGEST_MIN_HITS}+ hits',
    ]

    body = '\n'.join(lines)
    subject = f'[ryan-labeler] Weekly self-improve — {applied_count} rules auto-added'

    if args.dry_run:
        print('\n--- Email preview ---')
        print(body)
    else:
        sent = send_email(subject, body)
        print(f'  Report email: {"sent ✓" if sent else "FAILED"}')

    print('Done.')


if __name__ == '__main__':
    main()
