"""
Read-only audit of a client's Gmail inbox. Pulls N days of messages, computes
stats, optionally classifies each thread with Haiku, and writes a report.

Designed as the first step of a client engagement — gives us real sender and
subject patterns so the discovery email asks specific questions instead of
generic ones.

Usage:
    python3 tools/gmail_inbox_audit.py --client ryan --days 60 --classify

    # Re-run classification without re-fetching
    python3 tools/gmail_inbox_audit.py --client ryan --skip-fetch --classify

    # Quick test with a small window
    python3 tools/gmail_inbox_audit.py --client ryan --days 7 --limit 50

Prerequisites:
    1. GCP project "Enriquez OS" with Gmail API enabled
    2. OAuth consent screen in Testing mode with client's email as test user
    3. Desktop OAuth client JSON saved to:
       projects/personal/credentials_enriquez_os.json
    4. Client permission to read inbox (on record)

First run: browser opens — log in as the client, grant gmail.readonly.
Token saved per client at projects/personal/.tmp/clients/<slug>/token_<slug>.pickle.
"""

import argparse
import base64
import json
import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

BASE_DIR = Path(__file__).parent.parent
DEFAULT_CREDS = BASE_DIR / 'projects' / 'personal' / 'credentials_enriquez_os.json'
CLIENTS_DIR = BASE_DIR / 'projects' / 'personal' / '.tmp' / 'clients'
EPS_ENV = BASE_DIR / 'projects' / 'eps' / '.env'

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CATEGORIES = [
    'project',        # specific job/project emails with client/site
    'team_daily',     # daily updates from team members
    'bid_invite',     # invites to tender/bid on new work
    'promo',          # marketing, newsletters, sales pitches
    'vendor',         # supplier invoices, orders, quotes
    'client_inbound', # new customer inquiries
    'admin_ops',      # insurance, licensing, accounting, banking
    'personal',       # non-business
    'other',          # doesn't fit above
]


# ───────────────────────────────────────────────────────────── paths + auth

def client_paths(slug: str) -> dict:
    d = CLIENTS_DIR / slug
    return {
        'dir': d,
        'token': d / f'token_{slug}.pickle',
        'raw': d / 'raw-messages.jsonl',
        'classifications': d / 'classifications.json',
        'report': d / 'inbox-audit.md',
    }


def get_creds(token_path: Path, creds_path: Path):
    creds = None
    if token_path.exists():
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
            return creds
        except Exception as e:
            print(f"Token refresh failed ({e}) — running fresh OAuth flow", file=sys.stderr)

    if not creds_path.exists():
        print(f"ERROR: OAuth client JSON not found at {creds_path}", file=sys.stderr)
        print("Download from GCP → APIs & Services → Credentials → OAuth client (Desktop).", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path)
    return creds


def _save_token(creds, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(creds, f)


# ───────────────────────────────────────────────────────────── Gmail fetch

def list_message_ids(service, days: int, limit: Optional[int]) -> list:
    ids = []
    page_token = None
    query = f'newer_than:{days}d'
    while True:
        resp = service.users().messages().list(
            userId='me', q=query, pageToken=page_token, maxResults=500
        ).execute()
        for m in resp.get('messages', []):
            ids.append(m['id'])
            if limit and len(ids) >= limit:
                return ids
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return ids


def fetch_metadata_batch(service, ids: list, batch_size: int = 10) -> tuple:
    """Fetch message metadata. Returns (results, failed_ids).
    Small batches + per-chunk backoff to avoid Gmail's per-user concurrency cap."""
    results = []
    failed_all = []

    def make_cb(chunk_ids):
        def cb(req_id, response, exception):
            if exception:
                idx = int(req_id) if req_id and req_id.isdigit() else None
                failed_all.append(chunk_ids[idx] if idx is not None and idx < len(chunk_ids) else None)
            else:
                results.append(response)
        return cb

    total_chunks = (len(ids) + batch_size - 1) // batch_size
    for i, chunk_start in enumerate(range(0, len(ids), batch_size)):
        chunk = ids[chunk_start:chunk_start + batch_size]
        batch = service.new_batch_http_request(callback=make_cb(chunk))
        for msg_id in chunk:
            batch.add(service.users().messages().get(
                userId='me', id=msg_id, format='metadata',
                metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date', 'List-Unsubscribe']
            ))
        for attempt in range(4):
            try:
                batch.execute()
                break
            except HttpError as e:
                msg = str(e)
                if '429' in msg or 'rateLimit' in msg.lower() or 'concurrent' in msg.lower():
                    wait = 2 ** attempt + 0.5
                    print(f"  rate limit (chunk {i+1}/{total_chunks}, attempt {attempt+1}) — waiting {wait:.1f}s", file=sys.stderr)
                    time.sleep(wait)
                else:
                    print(f"  batch {chunk_start}: {e}", file=sys.stderr)
                    break
        if i % 20 == 19:
            print(f"  fetched {chunk_start + len(chunk)}/{len(ids)}...")
        time.sleep(0.15)

    failed_all = [f for f in failed_all if f]
    if failed_all:
        print(f"  {len(failed_all)} messages still failed after retries", file=sys.stderr)

    return results, failed_all


def normalize_message(raw: dict) -> dict:
    headers = {h['name'].lower(): h['value'] for h in raw.get('payload', {}).get('headers', [])}
    ts_ms = int(raw.get('internalDate', 0))
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else None
    return {
        'id': raw['id'],
        'thread_id': raw.get('threadId'),
        'label_ids': raw.get('labelIds', []),
        'snippet': raw.get('snippet', ''),
        'from': headers.get('from', ''),
        'to': headers.get('to', ''),
        'cc': headers.get('cc', ''),
        'subject': headers.get('subject', ''),
        'date': headers.get('date', ''),
        'internal_ts': ts_ms,
        'iso': dt.isoformat() if dt else None,
        'has_unsubscribe': bool(headers.get('list-unsubscribe')),
    }


def write_jsonl(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def append_jsonl(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def read_jsonl(path: Path) -> list:
    with open(path, 'r') as f:
        return [json.loads(line) for line in f if line.strip()]


# ───────────────────────────────────────────────────────────── stats

EMAIL_RE = re.compile(r'<([^>]+)>|([^\s<>]+@[^\s<>]+)')
NAME_RE = re.compile(r'^\s*"?([^"<]+?)"?\s*<')


def parse_from(raw: str) -> tuple:
    if not raw:
        return ('', '', '')
    name_m = NAME_RE.match(raw)
    name = name_m.group(1).strip() if name_m else ''
    em_m = EMAIL_RE.search(raw)
    email = ''
    if em_m:
        email = (em_m.group(1) or em_m.group(2) or '').strip().lower()
    domain = email.split('@')[-1] if '@' in email else ''
    return (name, email, domain)


def compute_stats(messages: list, labels: list) -> dict:
    label_by_id = {l['id']: l['name'] for l in labels}
    label_counts = Counter()
    sender_counts = Counter()
    domain_counts = Counter()
    day_counts = Counter()
    hour_counts = Counter()
    unsub_count = 0
    by_sender_domain = defaultdict(list)

    for m in messages:
        name, email, domain = parse_from(m['from'])
        if email:
            sender_counts[email] += 1
        if domain:
            domain_counts[domain] += 1
            by_sender_domain[domain].append(m['subject'][:80])
        for lid in m.get('label_ids', []):
            if lid in label_by_id:
                label_counts[label_by_id[lid]] += 1
        if m.get('internal_ts'):
            dt = datetime.fromtimestamp(m['internal_ts'] / 1000, tz=timezone.utc)
            day_counts[dt.date().isoformat()] += 1
            hour_counts[dt.hour] += 1
        if m.get('has_unsubscribe'):
            unsub_count += 1

    days_tracked = max(len(day_counts), 1)
    return {
        'total': len(messages),
        'days_tracked': len(day_counts),
        'avg_per_day': round(len(messages) / days_tracked, 1),
        'label_counts': label_counts.most_common(),
        'sender_counts': sender_counts.most_common(40),
        'domain_counts': domain_counts.most_common(30),
        'hour_counts': sorted(hour_counts.items()),
        'unsub_count': unsub_count,
        'by_sender_domain': {d: subs[:5] for d, subs in by_sender_domain.items()},
    }


# ───────────────────────────────────────────────────────────── classification

CLASSIFY_SYSTEM = f"""You classify emails from a contractor's inbox into ONE of these categories:

- project: emails about a specific active job/site (quotes, change orders, client check-ins about their job, scheduling for a specific address)
- team_daily: daily/regular updates from team members about work done or progress
- bid_invite: invitations to bid/tender on new work (ITB, RFP, bid opportunities, plan rooms)
- promo: marketing, newsletters, sales pitches, coupons, product announcements
- vendor: supplier communications — invoices, orders, quotes from suppliers, material confirmations
- client_inbound: brand-new inquiries from prospective clients asking for work
- admin_ops: insurance, licensing, accounting, banking, taxes, HR, legal
- personal: non-business (friends, family, personal subscriptions)
- other: doesn't fit above

For each email in the batch, return JSON: {{"id": "...", "category": "...", "project_hint": "<name or null>"}}
project_hint: if category=project, pull the client or site name from subject if visible, else null.

Rules:
- Return ONLY a JSON array. No prose. No markdown.
- One entry per input email, in order.
- If uncertain, use "other".
"""


def load_anthropic_key() -> str:
    if 'ANTHROPIC_API_KEY' in os.environ:
        return os.environ['ANTHROPIC_API_KEY']
    if EPS_ENV.exists():
        for line in EPS_ENV.read_text().splitlines():
            line = line.strip()
            if line.startswith('ANTHROPIC_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    print("ERROR: ANTHROPIC_API_KEY not found in env or projects/eps/.env", file=sys.stderr)
    sys.exit(1)


def classify_messages(messages: list, cache_path: Path) -> dict:
    import anthropic

    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    to_classify = [m for m in messages if m['id'] not in cache]
    if not to_classify:
        print(f"All {len(messages)} messages already classified (cached).")
        return cache

    client = anthropic.Anthropic(api_key=load_anthropic_key())
    batch_size = 40
    print(f"Classifying {len(to_classify)} messages in batches of {batch_size}...")

    for i in range(0, len(to_classify), batch_size):
        batch = to_classify[i:i + batch_size]
        payload = [
            {
                'id': m['id'],
                'from': m['from'][:200],
                'subject': m['subject'][:200],
                'snippet': m['snippet'][:300],
            }
            for m in batch
        ]
        user_msg = json.dumps(payload, indent=2)

        try:
            resp = client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=4000,
                system=[{
                    'type': 'text',
                    'text': CLASSIFY_SYSTEM,
                    'cache_control': {'type': 'ephemeral'},
                }],
                messages=[{'role': 'user', 'content': user_msg}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r'^```(?:json)?|```$', '', text, flags=re.MULTILINE).strip()
            parsed = json.loads(text)
            for row in parsed:
                if row.get('id'):
                    cache[row['id']] = {
                        'category': row.get('category', 'other'),
                        'project_hint': row.get('project_hint'),
                    }
        except Exception as e:
            print(f"Batch {i//batch_size} error: {e}", file=sys.stderr)

        if (i // batch_size) % 3 == 2:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, indent=2))
            print(f"  ...cached {len(cache)}/{len(messages)}")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2))
    return cache


def classification_stats(messages: list, classifications: dict) -> dict:
    by_cat = Counter()
    senders_by_cat = defaultdict(Counter)
    domains_by_cat = defaultdict(Counter)
    project_hints = Counter()

    for m in messages:
        c = classifications.get(m['id'])
        if not c:
            continue
        cat = c.get('category', 'other')
        by_cat[cat] += 1
        _, email, domain = parse_from(m['from'])
        if email:
            senders_by_cat[cat][email] += 1
        if domain:
            domains_by_cat[cat][domain] += 1
        if c.get('project_hint'):
            project_hints[c['project_hint']] += 1

    return {
        'by_category': by_cat.most_common(),
        'senders_by_cat': {k: v.most_common(8) for k, v in senders_by_cat.items()},
        'domains_by_cat': {k: v.most_common(8) for k, v in domains_by_cat.items()},
        'project_hints': project_hints.most_common(20),
    }


# ───────────────────────────────────────────────────────────── report

def render_report(slug: str, days: int, stats: dict, cstats: Optional[dict], labels: list) -> str:
    lines = []
    lines.append(f"# Inbox Audit — {slug}")
    lines.append("")
    lines.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} — window: last {days} days_")
    lines.append("")

    lines.append("## Volume")
    lines.append("")
    lines.append(f"- Total messages: **{stats['total']}**")
    lines.append(f"- Days covered: {stats['days_tracked']}")
    lines.append(f"- Avg per day: **{stats['avg_per_day']}**")
    lines.append(f"- Messages with `List-Unsubscribe` header (likely promo): {stats['unsub_count']}")
    lines.append("")

    if stats['hour_counts']:
        peak_hour, peak_count = max(stats['hour_counts'], key=lambda x: x[1])
        lines.append(f"- Peak receive hour (UTC): {peak_hour:02d}:00 ({peak_count} msgs)")
        lines.append("")

    lines.append("## Existing Gmail labels + usage")
    lines.append("")
    if stats['label_counts']:
        lines.append("| Label | Count |")
        lines.append("|---|---:|")
        for name, cnt in stats['label_counts']:
            lines.append(f"| {name} | {cnt} |")
    else:
        lines.append("_None found._")
    lines.append("")

    lines.append("## Top senders")
    lines.append("")
    lines.append("| Sender | Count |")
    lines.append("|---|---:|")
    for email, cnt in stats['sender_counts'][:25]:
        lines.append(f"| {email} | {cnt} |")
    lines.append("")

    lines.append("## Top domains")
    lines.append("")
    lines.append("| Domain | Count | Sample subjects |")
    lines.append("|---|---:|---|")
    for domain, cnt in stats['domain_counts'][:20]:
        samples = stats['by_sender_domain'].get(domain, [])
        s = '; '.join(s.replace('|', '/') for s in samples[:2]) or '—'
        lines.append(f"| {domain} | {cnt} | {s} |")
    lines.append("")

    if cstats:
        lines.append("## Classification (Haiku)")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        for cat, cnt in cstats['by_category']:
            lines.append(f"| **{cat}** | {cnt} |")
        lines.append("")

        for cat, _ in cstats['by_category']:
            domains = cstats['domains_by_cat'].get(cat, [])
            if not domains:
                continue
            lines.append(f"### {cat} — top domains")
            lines.append("")
            lines.append("| Domain | Count |")
            lines.append("|---|---:|")
            for dom, cnt in domains:
                lines.append(f"| {dom} | {cnt} |")
            lines.append("")

        if cstats['project_hints']:
            lines.append("### Detected project/client names")
            lines.append("")
            lines.append("| Name | Msg count |")
            lines.append("|---|---:|")
            for name, cnt in cstats['project_hints']:
                lines.append(f"| {name} | {cnt} |")
            lines.append("")

    lines.append("## Gaps — still need client input")
    lines.append("")
    lines.append("The inbox tells us senders, domains, volume, and patterns. It can't tell us:")
    lines.append("- What counts as \"urgent\" vs \"later\"")
    lines.append("- Which labels should auto-reply vs sit silent")
    lines.append("- Who on the team reads which buckets")
    lines.append("- Which promos to nuke vs keep")
    lines.append("- Preferred project naming convention going forward")
    lines.append("")
    lines.append("These become the questions in the discovery email.")
    lines.append("")

    return '\n'.join(lines)


# ───────────────────────────────────────────────────────────── main

def main():
    parser = argparse.ArgumentParser(description="Audit a client's Gmail inbox (read-only).")
    parser.add_argument('--client', required=True, help='Client slug (e.g. ryan)')
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--limit', type=int, default=None, help='Cap message count (for testing)')
    parser.add_argument('--classify', action='store_true', help='Run Haiku classification')
    parser.add_argument('--skip-fetch', action='store_true', dest='skip_fetch',
                        help='Skip Gmail fetch, reuse cached raw-messages.jsonl')
    parser.add_argument('--credentials', type=Path, default=DEFAULT_CREDS,
                        help=f'OAuth client JSON (default: {DEFAULT_CREDS})')
    args = parser.parse_args()

    paths = client_paths(args.client)
    paths['dir'].mkdir(parents=True, exist_ok=True)

    if args.skip_fetch:
        if not paths['raw'].exists():
            print(f"ERROR: --skip-fetch but {paths['raw']} missing", file=sys.stderr)
            sys.exit(1)
        print(f"Skipping fetch. Reading cached: {paths['raw']}")
        messages = read_jsonl(paths['raw'])
        labels = []
    else:
        print(f"Getting credentials for client: {args.client}")
        creds = get_creds(paths['token'], args.credentials)
        service = build('gmail', 'v1', credentials=creds)

        print("Fetching label list...")
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        print(f"  {len(labels)} labels.")

        print(f"Listing message IDs from last {args.days} days...")
        ids = list_message_ids(service, args.days, args.limit)
        print(f"  {len(ids)} message IDs.")

        if not ids:
            print("No messages in window. Done.")
            return

        existing_messages = []
        already_fetched = set()
        if paths['raw'].exists():
            existing_messages = read_jsonl(paths['raw'])
            already_fetched = {m['id'] for m in existing_messages}
            print(f"  {len(already_fetched)} already fetched from previous run — skipping those.")

        missing_ids = [i for i in ids if i not in already_fetched]
        print(f"  {len(missing_ids)} messages to fetch.")

        new_messages = []
        if missing_ids:
            print("Fetching metadata (small batches, with backoff)...")
            raw, failed = fetch_metadata_batch(service, missing_ids)
            new_messages = [normalize_message(r) for r in raw]
            print(f"  {len(new_messages)} new messages normalised. {len(failed)} failed.")
            append_jsonl(paths['raw'], new_messages)
            print(f"  Appended to: {paths['raw']}")

        messages = existing_messages + new_messages
        print(f"Total messages: {len(messages)}")

    print("Computing stats...")
    stats = compute_stats(messages, labels)

    cstats = None
    if args.classify:
        classifications = classify_messages(messages, paths['classifications'])
        cstats = classification_stats(messages, classifications)

    print("Writing report...")
    report = render_report(args.client, args.days, stats, cstats, labels)
    paths['report'].write_text(report)
    print(f"Report: {paths['report']}")


if __name__ == '__main__':
    main()
