"""
Coach-ICP outreach CLI — SQLite-backed. Distinct from outreach.py
(which is sheet-coupled for legacy PH biz pipeline).

Subcommands:
    discover --source skool|ig|linkedin --geo all --limit N
    enrich  --limit N
    list    --status enriched --segment coaches --geo all
    mark-sent --ids 1,2,3
    mark-replied --id N --classification INTERESTED|...
    stats

All operations read/write projects/personal/data/outreach.db.

Usage:
    python3 tools/personal/outreach_coach.py discover --source skool --limit 10
    python3 tools/personal/outreach_coach.py enrich --limit 20
    python3 tools/personal/outreach_coach.py list --status enriched
    python3 tools/personal/outreach_coach.py mark-sent --ids 1,3,5
"""

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

SHARED_ENV = BASE_DIR / 'projects' / '.env'
PERSONAL_ENV = BASE_DIR / 'projects' / 'personal' / '.env'


def load_env():
    for env_file in (SHARED_ENV, PERSONAL_ENV):
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def cmd_discover(args):
    from outreach_db import insert_prospect

    if args.source == 'skool':
        from outreach_sources.scrape_skool import scrape_skool
        prospects = scrape_skool(limit=args.limit, geo=args.geo)
    elif args.source == 'ig':
        from outreach_sources.scrape_ig import scrape_ig
        prospects = scrape_ig(limit=args.limit, geo=args.geo)
    elif args.source == 'linkedin':
        from outreach_sources.scrape_linkedin import scrape_linkedin
        prospects = scrape_linkedin(limit=args.limit, geo=args.geo)
    else:
        print(f"Unknown source: {args.source}", file=sys.stderr)
        return 1

    inserted = 0
    deduped = 0
    for p in prospects:
        p.setdefault('segment', 'coaches')
        p.setdefault('source', args.source)
        existing_count = inserted + deduped
        pid = insert_prospect(p)
        if pid:
            new_inserted = inserted + 1
            inserted = new_inserted
        else:
            deduped += 1
    print(f"[discover {args.source}] {inserted} new, {deduped} dedup, {len(prospects)} scraped total")
    return 0


def cmd_enrich(args):
    from outreach_db import list_prospects, update_prospect
    from outreach_enrich_coach import enrich_coach_prospect

    rows = list_prospects(status='discovered', segment='coaches', limit=args.limit)
    if not rows:
        print("[enrich] no rows in 'discovered'")
        return 0

    n_ok = n_skip = n_err = 0
    for row in rows:
        if isinstance(row.get('recent_posts_json'), str):
            try:
                row['recent_posts'] = json.loads(row['recent_posts_json'])
            except Exception:
                row['recent_posts'] = []
        try:
            updates = enrich_coach_prospect(row)
        except Exception as e:
            print(f"[enrich] {row['id']:>4d} ERROR: {e}", file=sys.stderr)
            n_err += 1
            continue
        if updates:
            update_prospect(row['id'], updates)
            print(f"[enrich] {row['id']:>4d} {row.get('name'):30s} -> {updates.get('sub_segment'):20s} variant {updates.get('hook_variant')}")
            n_ok += 1
        else:
            print(f"[enrich] {row['id']:>4d} {row.get('name'):30s} SKIPPED")
            n_skip += 1
    print(f"[enrich] done: {n_ok} ok, {n_skip} skipped, {n_err} errors")
    return 0


def cmd_list(args):
    from outreach_db import list_prospects
    rows = list_prospects(
        status=args.status,
        segment=args.segment or 'coaches',
        geo=args.geo,
        limit=args.limit,
    )
    if not rows:
        print("(no rows)")
        return 0
    for r in rows:
        print(f"  {r['id']:>4d} {r['status']:14s} {(r.get('geo') or '?'):4s} "
              f"{(r.get('name') or '')[:30]:30s} @{(r.get('ig_handle') or ''):25s} "
              f"{(r.get('sub_segment') or ''):18s} variant {(r.get('hook_variant') or '?')}")
    print(f"--- {len(rows)} rows")
    return 0


def cmd_mark_sent(args):
    from outreach_db import update_prospect
    ids = [int(s.strip()) for s in args.ids.split(',') if s.strip()]
    for pid in ids:
        update_prospect(pid, {'status': 'sent'})
    print(f"[mark-sent] updated {len(ids)} prospects")
    return 0


def cmd_mark_replied(args):
    from outreach_db import update_prospect
    update_prospect(args.id, {
        'status': 'replied',
        'reply_classification': args.classification,
        'reply_text': args.text or None,
    })
    print(f"[mark-replied] prospect {args.id}: {args.classification}")
    return 0


def cmd_stats(args):
    from outreach_db import stats
    rows = stats()
    if not rows:
        print("(empty)")
        return 0
    for r in rows:
        print(f"  {r['segment']:14s} {r['status']:18s} {r['n']:>6d}")
    return 0


def main():
    load_env()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    d = sub.add_parser('discover')
    d.add_argument('--source', required=True, choices=['skool', 'ig', 'linkedin'])
    d.add_argument('--geo', default='all', help='AU|US|UK|CA|PH|all')
    d.add_argument('--limit', type=int, default=10)
    d.set_defaults(func=cmd_discover)

    e = sub.add_parser('enrich')
    e.add_argument('--limit', type=int, default=20)
    e.set_defaults(func=cmd_enrich)

    l = sub.add_parser('list')
    l.add_argument('--status', default='enriched')
    l.add_argument('--segment')
    l.add_argument('--geo', default='all')
    l.add_argument('--limit', type=int, default=50)
    l.set_defaults(func=cmd_list)

    s = sub.add_parser('mark-sent')
    s.add_argument('--ids', required=True, help='comma-separated ids')
    s.set_defaults(func=cmd_mark_sent)

    r = sub.add_parser('mark-replied')
    r.add_argument('--id', type=int, required=True)
    r.add_argument('--classification', required=True,
                   choices=['INTERESTED', 'NOT_INTERESTED', 'QUESTION', 'OPTOUT', 'OTHER'])
    r.add_argument('--text', default='')
    r.set_defaults(func=cmd_mark_replied)

    st = sub.add_parser('stats')
    st.set_defaults(func=cmd_stats)

    args = p.parse_args()
    return args.func(args) or 0


if __name__ == '__main__':
    sys.exit(main())
