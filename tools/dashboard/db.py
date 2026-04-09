"""
SQLite cache layer for Enriquez OS Dashboard.

All reads/writes go through SQLite for instant response (<1ms).
Background sync pushes dirty rows to Google Sheets every 60s.
On startup, pulls full data from Sheets → SQLite.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from config import now_ph

DB_PATH = Path(__file__).parent / 'dashboard.db'
_local = threading.local()


def _conn():
    """Thread-local SQLite connection."""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute('PRAGMA journal_mode=WAL')
        _local.conn.execute('PRAGMA synchronous=NORMAL')
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS checklist_config (
            category TEXT NOT NULL,
            item TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'check',
            sort_order INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (category, item)
        );

        CREATE TABLE IF NOT EXISTS checklist_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            item TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            timestamp TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0,
            UNIQUE(date, item)
        );

        CREATE TABLE IF NOT EXISTS spend_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            amount REAL NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT '',
            timestamp TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sync_meta (
            table_name TEXT PRIMARY KEY,
            last_sync TEXT,
            direction TEXT
        );
    ''')
    conn.commit()


# ============================================================
# Checklist Config
# ============================================================

def load_config():
    """Load active checklist items grouped by category."""
    conn = _conn()
    rows = conn.execute(
        'SELECT category, item, type, sort_order FROM checklist_config '
        'WHERE active = 1 ORDER BY category, sort_order'
    ).fetchall()

    items_by_cat = {}
    for row in rows:
        cat = row['category']
        items_by_cat.setdefault(cat, []).append({
            'name': row['item'],
            'type': row['type'],
            'order': row['sort_order'],
        })
    return items_by_cat


def save_config(rows):
    """Bulk upsert config from Sheets data. rows = list of [category, item, type, order, active]."""
    conn = _conn()
    conn.executemany(
        'INSERT OR REPLACE INTO checklist_config (category, item, type, sort_order, active) '
        'VALUES (?, ?, ?, ?, ?)',
        [(r[0], r[1], r[2], int(r[3]) if r[3].isdigit() else 0,
          1 if len(r) < 5 or r[4].upper() == 'TRUE' else 0)
         for r in rows]
    )
    conn.commit()


# ============================================================
# Checklist Log
# ============================================================

def load_log(date):
    """Load checklist completions for a date. Returns {item: value}."""
    conn = _conn()
    rows = conn.execute(
        'SELECT item, value FROM checklist_log WHERE date = ?', (date,)
    ).fetchall()
    return {row['item']: row['value'] for row in rows}


def load_log_range(start_date, end_date):
    """Load checklist completions for a date range. Returns {date: {item: value}}."""
    conn = _conn()
    rows = conn.execute(
        'SELECT date, item, value FROM checklist_log WHERE date >= ? AND date <= ?',
        (start_date, end_date)
    ).fetchall()
    result = {}
    for row in rows:
        result.setdefault(row['date'], {})[row['item']] = row['value']
    return result


def save_toggle(date, item, value):
    """Save a checklist toggle/count. Returns immediately."""
    conn = _conn()
    timestamp = now_ph().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        'INSERT INTO checklist_log (date, item, value, timestamp, synced) '
        'VALUES (?, ?, ?, ?, 0) '
        'ON CONFLICT(date, item) DO UPDATE SET value=?, timestamp=?, synced=0',
        (date, item, value, timestamp, value, timestamp)
    )
    conn.commit()


def save_log_bulk(rows):
    """Bulk upsert log entries from Sheets. rows = list of [date, item, value, timestamp]."""
    conn = _conn()
    conn.executemany(
        'INSERT OR REPLACE INTO checklist_log (date, item, value, timestamp, synced) '
        'VALUES (?, ?, ?, ?, 1)',
        [(r[0], r[1], r[2], r[3] if len(r) > 3 else '') for r in rows if len(r) >= 3]
    )
    conn.commit()


# ============================================================
# Spend Log
# ============================================================

def load_spend(date):
    """Load spend entries for a date."""
    conn = _conn()
    rows = conn.execute(
        'SELECT id, date, category, amount, description, timestamp FROM spend_log '
        'WHERE date = ? ORDER BY id', (date,)
    ).fetchall()
    return [dict(row) for row in rows]


def load_spend_range(start_date, end_date):
    """Load spend entries for a date range."""
    conn = _conn()
    rows = conn.execute(
        'SELECT date, category, amount FROM spend_log '
        'WHERE date >= ? AND date <= ?', (start_date, end_date)
    ).fetchall()
    return [dict(row) for row in rows]


def save_spend(date, category, amount, description):
    """Add a spend entry."""
    conn = _conn()
    timestamp = now_ph().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        'INSERT INTO spend_log (date, category, amount, description, timestamp, synced) '
        'VALUES (?, ?, ?, ?, ?, 0)',
        (date, category, float(amount), description, timestamp)
    )
    conn.commit()


def delete_spend(spend_id):
    """Delete a spend entry by ID."""
    conn = _conn()
    conn.execute('DELETE FROM spend_log WHERE id = ?', (spend_id,))
    conn.commit()


def save_spend_bulk(rows):
    """Bulk insert spend entries from Sheets. rows = list of [date, category, amount, description, timestamp]."""
    conn = _conn()
    conn.executemany(
        'INSERT INTO spend_log (date, category, amount, description, timestamp, synced) '
        'VALUES (?, ?, ?, ?, ?, 1)',
        [(r[0], r[1], float(r[2]) if r[2] else 0, r[3] if len(r) > 3 else '',
          r[4] if len(r) > 4 else '') for r in rows if len(r) >= 3 and r[0]]
    )
    conn.commit()


# ============================================================
# Sync helpers
# ============================================================

def get_unsynced_log():
    """Get checklist log entries that haven't been synced to Sheets."""
    conn = _conn()
    rows = conn.execute(
        'SELECT id, date, item, value, timestamp FROM checklist_log WHERE synced = 0'
    ).fetchall()
    return [dict(row) for row in rows]


def get_unsynced_spend():
    """Get spend entries that haven't been synced to Sheets."""
    conn = _conn()
    rows = conn.execute(
        'SELECT id, date, category, amount, description, timestamp FROM spend_log WHERE synced = 0'
    ).fetchall()
    return [dict(row) for row in rows]


def mark_log_synced(ids):
    """Mark checklist log entries as synced."""
    if not ids:
        return
    conn = _conn()
    placeholders = ','.join('?' * len(ids))
    conn.execute(f'UPDATE checklist_log SET synced = 1 WHERE id IN ({placeholders})', ids)
    conn.commit()


def mark_spend_synced(ids):
    """Mark spend entries as synced."""
    if not ids:
        return
    conn = _conn()
    placeholders = ','.join('?' * len(ids))
    conn.execute(f'UPDATE spend_log SET synced = 1 WHERE id IN ({placeholders})', ids)
    conn.commit()


def update_sync_meta(table_name, direction='push'):
    """Update last sync timestamp."""
    conn = _conn()
    ts = now_ph().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        'INSERT OR REPLACE INTO sync_meta (table_name, last_sync, direction) VALUES (?, ?, ?)',
        (table_name, ts, direction)
    )
    conn.commit()


def is_empty():
    """Check if the database has any data (used to determine if initial sync needed)."""
    conn = _conn()
    count = conn.execute('SELECT COUNT(*) FROM checklist_config').fetchone()[0]
    return count == 0
