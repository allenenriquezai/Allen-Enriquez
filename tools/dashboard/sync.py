"""
Background sync between SQLite (fast) and Google Sheets (source of truth).

- On startup: full pull from Sheets → SQLite
- Every 60s: push dirty rows from SQLite → Sheets
"""

import threading
import time
import traceback

import db


def sync_from_sheets(sheets_service, sheet_id):
    """Full pull from Sheets → SQLite. Run once on startup."""
    try:
        print("[sync] Pulling from Sheets → SQLite...")

        # 1. Checklist Config
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="'Checklist Config'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) > 1:
            db.save_config(rows[1:])
            print(f"[sync]   Config: {len(rows) - 1} items")

        # 2. Checklist Log
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="'Checklist Log'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) > 1:
            db.save_log_bulk(rows[1:])
            print(f"[sync]   Log: {len(rows) - 1} entries")

        # 3. Spend Log
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="'Spend Log'"
        ).execute()
        rows = result.get('values', [])
        if len(rows) > 1:
            db.save_spend_bulk(rows[1:])
            print(f"[sync]   Spend: {len(rows) - 1} entries")

        db.update_sync_meta('all', 'pull')
        print("[sync] Pull complete.")

    except Exception as e:
        print(f"[sync] Pull failed: {e}")
        traceback.print_exc()


def sync_to_sheets(sheets_service, sheet_id):
    """Push dirty rows from SQLite → Sheets."""
    try:
        # 1. Checklist Log — unsynced entries
        unsynced_log = db.get_unsynced_log()
        if unsynced_log:
            # Read existing log to find rows to update vs append
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range="'Checklist Log'"
            ).execute()
            existing = result.get('values', [])

            # Build index: (date, item) → row number
            existing_idx = {}
            for i, row in enumerate(existing[1:], start=2):
                if len(row) >= 2:
                    existing_idx[(row[0], row[1])] = i

            updates = []
            appends = []
            for entry in unsynced_log:
                key = (entry['date'], entry['item'])
                if key in existing_idx:
                    row_num = existing_idx[key]
                    updates.append({
                        'range': f"'Checklist Log'!C{row_num}:D{row_num}",
                        'values': [[entry['value'], entry['timestamp']]],
                    })
                else:
                    appends.append([entry['date'], entry['item'], entry['value'], entry['timestamp']])

            if updates:
                sheets_service.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'valueInputOption': 'RAW', 'data': updates},
                ).execute()

            if appends:
                sheets_service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range="'Checklist Log'!A:D",
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body={'values': appends},
                ).execute()

            db.mark_log_synced([e['id'] for e in unsynced_log])
            print(f"[sync] Pushed {len(unsynced_log)} checklist entries (updated: {len(updates)}, new: {len(appends)})")

        # 2. Spend Log — unsynced entries
        unsynced_spend = db.get_unsynced_spend()
        if unsynced_spend:
            rows = [
                [e['date'], e['category'], str(e['amount']), e['description'], e['timestamp']]
                for e in unsynced_spend
            ]
            sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range="'Spend Log'!A:E",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': rows},
            ).execute()

            db.mark_spend_synced([e['id'] for e in unsynced_spend])
            print(f"[sync] Pushed {len(unsynced_spend)} spend entries")

        if unsynced_log or unsynced_spend:
            db.update_sync_meta('all', 'push')

    except Exception as e:
        print(f"[sync] Push failed: {e}")
        traceback.print_exc()


_sync_thread = None
_stop_event = threading.Event()


def start_background_sync(sheets_service, sheet_id, interval=60):
    """Start background thread that pushes dirty rows every `interval` seconds."""
    global _sync_thread

    def _loop():
        while not _stop_event.is_set():
            _stop_event.wait(interval)
            if _stop_event.is_set():
                break
            sync_to_sheets(sheets_service, sheet_id)

    _sync_thread = threading.Thread(target=_loop, daemon=True, name='sheets-sync')
    _sync_thread.start()
    print(f"[sync] Background sync started (every {interval}s)")


def stop_background_sync():
    """Stop the background sync thread."""
    _stop_event.set()
    if _sync_thread:
        _sync_thread.join(timeout=5)
