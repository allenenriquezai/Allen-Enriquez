"""
PH Outbound Outreach System.

Unified CLI for the end-to-end outbound pipeline: discover -> enrich ->
queue -> log-sent -> followups -> replies -> stats.

Automates everything up to the send step. Allen reviews + sends manually
from his Gmail / FB / IG.

Subcommands:
    discover   Pull new prospects from all sources (Places API, scrapers, FB
               inbox) into the PH Outreach Sheet. Weekly cron.
    enrich     Enrich status=new rows (website scrape, email finder, FB
               Graph, Haiku personal hook). Daily cron.
    queue      Generate today's outreach queue as .tmp/outreach_queue_YYYY-MM-DD.md
               respecting daily limits. Daily cron.
    log-sent   Mark prospects as sent after Allen finishes the queue.
               --ids 1,3,5 (row numbers from today's queue)
    followups  Detect due follow-ups (Touch 2, Touch 3). Daily cron.
    replies    Poll Gmail INBOX for replies, draft AI responses for approval.
               Daily cron.
    stats      Funnel report: discovered / enriched / sent / replied / warm / converted.

Requires:
    projects/personal/token_personal_ai.pickle      (Sheets + Gmail)
    projects/personal/.env                       (ANTHROPIC_API_KEY, optional
                                                  GOOGLE_PLACES_API_KEY, SNOV_API_KEY,
                                                  HUNTER_API_KEY, FB_GRAPH_TOKEN)
    projects/personal/reference/outreach_config.yaml

Usage:
    python3 tools/outreach.py discover --segment recruitment --limit 20
    python3 tools/outreach.py enrich --limit 10
    python3 tools/outreach.py queue
    python3 tools/outreach.py log-sent --ids 1,2,4
    python3 tools/outreach.py followups
    python3 tools/outreach.py replies
    python3 tools/outreach.py stats
"""

import argparse
import os
import pickle
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from outreach_enrich import enrich_prospect
from outreach_messages import render_message, generate_queue_markdown
from outreach_lifecycle import (
    log_sent as lifecycle_log_sent,
    detect_followups, poll_replies_and_draft,
)

BASE_DIR = Path(__file__).parent.parent
SHARED_ENV = BASE_DIR / 'projects' / '.env'
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
ENV_FILE = BASE_DIR / 'projects' / 'personal' / '.env'
CONFIG_FILE = BASE_DIR / 'projects' / 'personal' / 'reference' / 'outreach_config.yaml'
TMP_DIR = BASE_DIR / 'projects' / 'personal' / '.tmp'
TEMPLATE_DIR = BASE_DIR / 'projects' / 'personal' / 'templates' / 'outreach'
FB_INBOX = TMP_DIR / 'fb_prospects_inbox.txt'

PH_TZ = timezone(timedelta(hours=8))


# ============================================================
# Config + env loading
# ============================================================

def load_env():
    """Load shared then personal .env into os.environ."""
    for env_file in [SHARED_ENV, ENV_FILE]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config():
    """Load outreach_config.yaml. Dies if missing required keys."""
    try:
        import yaml
    except ImportError:
        print("ERROR: pyyaml not installed. Run: pip3 install pyyaml", file=sys.stderr)
        sys.exit(1)
    if not CONFIG_FILE.exists():
        print(f"ERROR: config not found at {CONFIG_FILE}", file=sys.stderr)
        sys.exit(1)
    cfg = yaml.safe_load(CONFIG_FILE.read_text())
    if not cfg.get('spreadsheet_id'):
        print("ERROR: spreadsheet_id missing in outreach_config.yaml.", file=sys.stderr)
        print("Run: python3 tools/setup_ph_outreach_sheet.py", file=sys.stderr)
        sys.exit(1)
    return cfg


# ============================================================
# Google creds + Sheets helpers
# ============================================================

def get_creds():
    from google.auth.transport.requests import Request
    if not TOKEN_FILE.exists():
        print(f"ERROR: Personal token not found at {TOKEN_FILE}", file=sys.stderr)
        print("Run: python3 tools/auth_personal.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def sheets_service():
    from googleapiclient.discovery import build
    return build('sheets', 'v4', credentials=get_creds())


def col_letter(index):
    """0-based column index -> letter (0=A, 26=AA)."""
    result = ''
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


def read_prospects(svc, spreadsheet_id):
    """Return (headers, rows) for Prospects tab. Rows are dicts with _row index."""
    r = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="Prospects"
    ).execute()
    values = r.get('values', [])
    if not values:
        return [], []
    headers = values[0]
    rows = []
    for i, row in enumerate(values[1:], start=2):
        padded = row + [''] * (len(headers) - len(row))
        rows.append({'_row': i, **{h: padded[j] for j, h in enumerate(headers)}})
    return headers, rows


def write_cell(svc, spreadsheet_id, headers, row_num, field, value):
    if field not in headers:
        raise ValueError(f"column {field!r} not in sheet")
    letter = col_letter(headers.index(field))
    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Prospects!{letter}{row_num}",
        valueInputOption='RAW',
        body={'values': [[value]]},
    ).execute()


def append_row(svc, spreadsheet_id, headers, row_dict):
    row = [row_dict.get(h, '') for h in headers]
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Prospects",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': [row]},
    ).execute()


# ============================================================
# Warm-up ramp
# ============================================================

def current_email_limit(cfg):
    """Resolve today's email limit per warmup ramp + absolute cap."""
    ramp = cfg['limits']['email_warmup_ramp']
    start = datetime.strptime(cfg['limits']['warmup_start_date'], '%Y-%m-%d').date()
    today = datetime.now(PH_TZ).date()
    weeks = max(0, (today - start).days // 7)
    idx = min(weeks, len(ramp) - 1)
    return min(ramp[idx], cfg['guardrails']['max_email_per_day_absolute'])


def current_fb_limit(cfg):
    return min(cfg['limits']['fb_dm_per_day'],
               cfg['guardrails']['max_fb_dm_per_day_absolute'])


# ============================================================
# Subcommands (stubs — Phase 2+ will fill)
# ============================================================

def cmd_discover(args, cfg):
    from outreach_sources import (
        discover_google_places, discover_businesslist, discover_jobstreet,
        discover_kalibrr, discover_fb_inbox, dedupe_prospects,
    )
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    headers, existing = read_prospects(svc, sid)

    segments = [args.segment] if args.segment else list(cfg['segments'].keys())
    sources = [args.source] if args.source else ['places', 'businesslist', 'jobstreet', 'kalibrr', 'fb_inbox']

    new_prospects = []
    places_key = os.environ.get('GOOGLE_PLACES_API_KEY', '')

    for seg in segments:
        seg_cfg = cfg['segments'][seg]
        if 'places' in sources:
            new_prospects += discover_google_places(
                places_key, seg_cfg.get('google_places_queries', []), seg, args.limit
            )
        if 'businesslist' in sources:
            categories = {'recruitment': 'recruitment-agencies',
                          'real_estate': 'real-estate-agents'}.get(seg)
            cities = ['manila', 'cebu', 'quezon-city', 'makati', 'davao']
            if categories:
                new_prospects += discover_businesslist([categories], cities, seg, args.limit)
        if 'jobstreet' in sources and seg_cfg.get('jobstreet_search_terms'):
            new_prospects += discover_jobstreet(
                seg_cfg['jobstreet_search_terms'], seg, args.limit
            )
        if 'kalibrr' in sources and seg_cfg.get('kalibrr_search_terms'):
            new_prospects += discover_kalibrr(
                seg_cfg['kalibrr_search_terms'], seg, args.limit
            )

    if 'fb_inbox' in sources and FB_INBOX.exists():
        new_prospects += discover_fb_inbox(FB_INBOX)

    deduped = dedupe_prospects(new_prospects, existing)
    print(f"[discover] raw: {len(new_prospects)}  deduped: {len(deduped)}")

    if args.dry_run:
        for p in deduped[:5]:
            print(f"  - {p.get('Company', p.get('Name', '?'))} | {p.get('Segment')} | {p.get('Source')}")
        print("(dry-run: no writes)")
        return 0

    for p in deduped:
        p.setdefault('Status', 'new')
        p.setdefault('Date Added', datetime.now(PH_TZ).date().isoformat())
        append_row(svc, sid, headers, p)

    print(f"[discover] wrote {len(deduped)} new prospects to sheet")
    return 0


def cmd_enrich(args, cfg):
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    headers, rows = read_prospects(svc, sid)

    to_enrich = []
    for r in rows:
        if args.row and r['_row'] != args.row:
            continue
        if r.get('Status', '').strip() in ('new', ''):
            to_enrich.append(r)
    to_enrich = to_enrich[:args.limit]

    if not to_enrich:
        print("[enrich] nothing to enrich. Run discover first.")
        return 0

    env = dict(os.environ)
    enriched_count = 0
    for row in to_enrich:
        company = row.get('Company', row.get('Name', '?'))
        print(f"[enrich] {company} (row {row['_row']})")
        updates = enrich_prospect(row, env)
        if args.dry_run:
            for k, v in updates.items():
                v_short = (v[:80] + '...') if isinstance(v, str) and len(v) > 80 else v
                print(f"    {k}: {v_short}")
            continue
        for field, val in updates.items():
            if field in headers:
                write_cell(svc, sid, headers, row['_row'], field, val)
        enriched_count += 1

    print(f"[enrich] {'dry-run: would enrich' if args.dry_run else 'enriched'} {enriched_count if not args.dry_run else len(to_enrich)} rows")
    return 0


def cmd_queue(args, cfg):
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    headers, rows = read_prospects(svc, sid)

    today = datetime.now(PH_TZ).date()
    email_limit = current_email_limit(cfg)
    fb_limit = current_fb_limit(cfg)

    email_candidates = []
    fb_candidates = []
    for r in rows:
        status = r.get('Status', '').strip()
        if status != 'enriched':
            continue
        if r.get('Email', '').strip() and len(email_candidates) < email_limit:
            email_candidates.append(r)
        elif r.get('FB URL', '').strip() and len(fb_candidates) < fb_limit:
            fb_candidates.append(r)

    print(f"[queue] email: {len(email_candidates)}/{email_limit}  fb: {len(fb_candidates)}/{fb_limit}")

    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    queue = []

    for r in email_candidates:
        seg_cfg = cfg['segments'].get(r.get('Segment', ''), {})
        msg = render_message(r, seg_cfg, 'email', 1, anthropic_key)
        queue.append({
            'prospect': r, 'channel': 'email', 'touch': 1,
            'subject': msg.get('subject'), 'body': msg['body'],
            'row_num': r['_row'],
        })

    for r in fb_candidates:
        seg_cfg = cfg['segments'].get(r.get('Segment', ''), {})
        msg = render_message(r, seg_cfg, 'fb', 1, anthropic_key)
        queue.append({
            'prospect': r, 'channel': 'fb', 'touch': 1,
            'subject': None, 'body': msg['body'],
            'row_num': r['_row'],
        })

    if not queue:
        print("[queue] nothing ready. Run enrich first.")
        return 0

    md = generate_queue_markdown(queue, {'email': email_limit, 'fb_dm': fb_limit})
    out = TMP_DIR / f'outreach_queue_{today}.md'
    if args.dry_run:
        print(f"(dry-run) would write {len(queue)} messages to {out}")
        print("--- preview ---")
        print(md[:1200])
        return 0

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"[queue] wrote {len(queue)} messages -> {out}")
    return 0


def cmd_log_sent(args, cfg):
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    headers, _ = read_prospects(svc, sid)
    today = datetime.now(PH_TZ).date()
    queue_file = TMP_DIR / f'outreach_queue_{today}.md'
    if not queue_file.exists():
        print(f"[log-sent] today's queue file not found: {queue_file}")
        return 1
    ids = [int(x.strip()) for x in args.ids.split(',') if x.strip()]
    result = lifecycle_log_sent(ids, svc, sid, headers, queue_file)
    print(f"[log-sent] marked {result.get('marked', 0)} rows sent")
    if result.get('errors'):
        for err in result['errors']:
            print(f"  error: {err}")
    return 0


def cmd_followups(args, cfg):
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    today = datetime.now(PH_TZ).date()
    due = detect_followups(svc, sid, cfg['limits']['followup_wait_days'], today)
    print(f"[followups] {len(due)} follow-ups due today")
    for d in due:
        print(f"  row {d['_row']}: {d.get('company', '?')} T{d['current_touch']} -> T{d['next_touch']} via {d['channel']}")
    return 0


def cmd_replies(args, cfg):
    from googleapiclient.discovery import build
    svc = sheets_service()
    sid = cfg['spreadsheet_id']
    headers, _ = read_prospects(svc, sid)
    gmail = build('gmail', 'v1', credentials=get_creds())
    drafts_file = TMP_DIR / 'reply_drafts.md'
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    result = poll_replies_and_draft(gmail, svc, sid, headers, anthropic_key, drafts_file)
    print(f"[replies] inbound={result.get('inbound',0)} drafts={result.get('drafts_written',0)} optouts={result.get('optouts',0)}")
    if result.get('drafts_written'):
        print(f"  drafts at: {drafts_file}")
    return 0


def cmd_stats(args, cfg):
    """Funnel report. Works now — reads Sheet directly."""
    svc = sheets_service()
    headers, rows = read_prospects(svc, cfg['spreadsheet_id'])
    total = len(rows)
    if total == 0:
        print("No prospects yet. Run discover first.")
        return 0

    by_status = {}
    by_segment = {}
    for r in rows:
        s = r.get('Status', '').strip() or '(blank)'
        seg = r.get('Segment', '').strip() or '(none)'
        by_status[s] = by_status.get(s, 0) + 1
        by_segment[seg] = by_segment.get(seg, 0) + 1

    print("=== PH Outreach funnel ===")
    print(f"Total prospects: {total}")
    print(f"\nBy status:")
    for s, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<25} {n}")
    print(f"\nBy segment:")
    for s, n in sorted(by_segment.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<25} {n}")

    today = datetime.now(PH_TZ).date()
    print(f"\nToday's limits: {current_email_limit(cfg)} emails / {current_fb_limit(cfg)} FB DMs")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{cfg['spreadsheet_id']}/edit")
    return 0


# ============================================================
# CLI
# ============================================================

def main():
    p = argparse.ArgumentParser(prog='outreach', description=__doc__.split('\n')[1])
    sub = p.add_subparsers(dest='cmd')

    d = sub.add_parser('discover', help='Pull new prospects')
    d.add_argument('--segment', choices=['recruitment', 'real_estate'])
    d.add_argument('--limit', type=int, default=50)
    d.add_argument('--source', choices=['places', 'businesslist', 'jobstreet', 'kalibrr', 'fb_inbox'])
    d.add_argument('--dry-run', action='store_true')

    e = sub.add_parser('enrich', help='Enrich status=new rows')
    e.add_argument('--limit', type=int, default=10)
    e.add_argument('--row', type=int, help='Target a single row')
    e.add_argument('--dry-run', action='store_true')

    q = sub.add_parser('queue', help="Generate today's outreach queue")
    q.add_argument('--dry-run', action='store_true')

    ls = sub.add_parser('log-sent', help='Mark prospects as sent')
    ls.add_argument('--ids', required=True, help='Comma-separated row numbers')

    sub.add_parser('followups', help='Detect due follow-ups')
    sub.add_parser('replies', help='Poll Gmail for replies, draft responses')
    sub.add_parser('stats', help='Funnel report')

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1

    load_env()
    cfg = load_config()

    dispatch = {
        'discover': cmd_discover,
        'enrich': cmd_enrich,
        'queue': cmd_queue,
        'log-sent': cmd_log_sent,
        'followups': cmd_followups,
        'replies': cmd_replies,
        'stats': cmd_stats,
    }
    return dispatch[args.cmd](args, cfg) or 0


if __name__ == '__main__':
    sys.exit(main())
