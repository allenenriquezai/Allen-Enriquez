"""
Outreach SQLite DB — single source of truth for cold-DM prospects + ad-leads.

Replaces the sheet-based PH Outreach pipeline as the data backend for the
coach ICP outreach factory. Existing PH Outreach Sheet stays untouched
for legacy recruitment/VA prospects.

Schema lives in outreach_prospects table. Status flow:
    discovered -> enriched -> queued -> sent -> replied -> discovery_booked
                                              -> no_reply / not_now / optout
    ad-lead (entry from landing form) -> queued (after auto-DM bridge fires)

CLI:
    python3 tools/personal/outreach_db.py migrate
    python3 tools/personal/outreach_db.py stats
    python3 tools/personal/outreach_db.py vacuum
"""

import argparse
import json
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / 'projects' / 'personal' / 'data' / 'outreach.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS outreach_prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    segment TEXT NOT NULL,
    sub_segment TEXT,
    name TEXT NOT NULL,
    ig_handle TEXT,
    ig_url TEXT,
    skool_url TEXT,
    linkedin_url TEXT,
    email TEXT,
    geo TEXT,
    audience_size INTEGER,
    community_name TEXT,
    community_size INTEGER,
    community_price_usd INTEGER,
    profile_pic_url TEXT,
    bio TEXT,
    recent_posts_json TEXT,
    pain_signal TEXT,
    recent_post_topic TEXT,
    personal_hook TEXT,
    hook_variant TEXT,
    source TEXT NOT NULL,
    source_query TEXT,
    status TEXT DEFAULT 'discovered' NOT NULL,
    discovered_at TEXT,
    enriched_at TEXT,
    queued_at TEXT,
    sent_at TEXT,
    reply_received_at TEXT,
    reply_classification TEXT,
    reply_text TEXT,
    notes TEXT,
    raw_payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_prospects(status);
CREATE INDEX IF NOT EXISTS idx_outreach_segment ON outreach_prospects(segment);
CREATE INDEX IF NOT EXISTS idx_outreach_geo ON outreach_prospects(geo);
CREATE INDEX IF NOT EXISTS idx_outreach_source ON outreach_prospects(source);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_ig_handle ON outreach_prospects(ig_handle) WHERE ig_handle IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_skool_url ON outreach_prospects(skool_url) WHERE skool_url IS NOT NULL;

CREATE TABLE IF NOT EXISTS outreach_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (prospect_id) REFERENCES outreach_prospects(id)
);

CREATE INDEX IF NOT EXISTS idx_events_prospect ON outreach_events(prospect_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON outreach_events(event_type);
"""

VALID_STATUSES = {
    'discovered', 'enriched', 'queued', 'sent',
    'replied', 'discovery_booked', 'pilot_active', 'retainer_signed',
    'no_reply', 'not_now', 'optout',
    'ad-lead',
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextmanager
def get_conn(db_path=DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate(db_path=DB_PATH):
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)
    print(f"[outreach_db] migrated: {db_path}")


def insert_prospect(prospect, db_path=DB_PATH):
    """Insert or no-op-update a prospect row.

    Dedup via unique indexes on ig_handle and skool_url. If exists, returns existing id.
    `prospect` is a dict matching column names. `recent_posts` may be a list (will be JSON-encoded).
    """
    cols = [
        'segment', 'sub_segment', 'name', 'ig_handle', 'ig_url', 'skool_url',
        'linkedin_url', 'email', 'geo', 'audience_size', 'community_name',
        'community_size', 'community_price_usd', 'profile_pic_url', 'bio',
        'pain_signal', 'recent_post_topic', 'personal_hook', 'hook_variant',
        'source', 'source_query', 'status', 'discovered_at', 'notes',
    ]
    row = {k: prospect.get(k) for k in cols}
    if not row.get('status'):
        row['status'] = 'discovered'
    if not row.get('discovered_at'):
        row['discovered_at'] = now_iso()

    posts = prospect.get('recent_posts')
    row['recent_posts_json'] = json.dumps(posts) if posts is not None else None

    raw = prospect.get('raw_payload')
    row['raw_payload_json'] = json.dumps(raw) if raw is not None else None

    all_cols = cols + ['recent_posts_json', 'raw_payload_json']
    placeholders = ','.join(['?'] * len(all_cols))
    col_list = ','.join(all_cols)
    values = [row.get(c) for c in all_cols]

    with get_conn(db_path) as conn:
        existing_id = None
        if row.get('ig_handle'):
            cur = conn.execute("SELECT id FROM outreach_prospects WHERE ig_handle = ?", (row['ig_handle'],))
            r = cur.fetchone()
            existing_id = r['id'] if r else None
        if not existing_id and row.get('skool_url'):
            cur = conn.execute("SELECT id FROM outreach_prospects WHERE skool_url = ?", (row['skool_url'],))
            r = cur.fetchone()
            existing_id = r['id'] if r else None

        if existing_id:
            return existing_id

        cur = conn.execute(
            f"INSERT INTO outreach_prospects ({col_list}) VALUES ({placeholders})",
            values,
        )
        new_id = cur.lastrowid
        conn.execute(
            "INSERT INTO outreach_events (prospect_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (new_id, 'discovered', json.dumps({'source': row.get('source')}), now_iso()),
        )
        return new_id


def update_prospect(prospect_id, fields, db_path=DB_PATH):
    """Update a prospect with the given field dict. Auto-stamps timestamp for status changes."""
    if 'status' in fields and fields['status'] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {fields['status']}")

    if fields.get('status') == 'enriched' and 'enriched_at' not in fields:
        fields['enriched_at'] = now_iso()
    if fields.get('status') == 'queued' and 'queued_at' not in fields:
        fields['queued_at'] = now_iso()
    if fields.get('status') == 'sent' and 'sent_at' not in fields:
        fields['sent_at'] = now_iso()
    if fields.get('status') == 'replied' and 'reply_received_at' not in fields:
        fields['reply_received_at'] = now_iso()

    posts = fields.pop('recent_posts', None)
    if posts is not None:
        fields['recent_posts_json'] = json.dumps(posts)

    if not fields:
        return

    set_clause = ','.join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [prospect_id]

    with get_conn(db_path) as conn:
        conn.execute(f"UPDATE outreach_prospects SET {set_clause} WHERE id = ?", values)
        if 'status' in fields:
            conn.execute(
                "INSERT INTO outreach_events (prospect_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (prospect_id, f"status:{fields['status']}", json.dumps(fields), now_iso()),
            )


def list_prospects(status=None, segment=None, geo=None, limit=None, db_path=DB_PATH):
    where = []
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if segment:
        where.append("segment = ?")
        params.append(segment)
    if geo and geo != 'all':
        where.append("geo = ?")
        params.append(geo)
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    limit_sql = f'LIMIT {int(limit)}' if limit else ''
    sql = f"SELECT * FROM outreach_prospects {where_sql} ORDER BY id DESC {limit_sql}"
    with get_conn(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_prospect(prospect_id, db_path=DB_PATH):
    with get_conn(db_path) as conn:
        r = conn.execute("SELECT * FROM outreach_prospects WHERE id = ?", (prospect_id,)).fetchone()
        return dict(r) if r else None


def stats(db_path=DB_PATH):
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT segment, status, COUNT(*) as n FROM outreach_prospects GROUP BY segment, status ORDER BY segment, status"
        ).fetchall()
        return [dict(r) for r in rows]


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('migrate')
    sub.add_parser('stats')
    sub.add_parser('vacuum')
    args = p.parse_args()

    if args.cmd == 'migrate':
        migrate()
    elif args.cmd == 'stats':
        for r in stats():
            print(f"  {r['segment']:20s} {r['status']:20s} {r['n']:>6d}")
    elif args.cmd == 'vacuum':
        with get_conn() as conn:
            conn.execute('VACUUM')
        print('[outreach_db] vacuumed')


if __name__ == '__main__':
    main()
