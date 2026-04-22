"""
Fetch data from Gmail (EPS + personal), Google Calendar, and Pipedrive
for the /os-review skill.

Outputs: .tmp/review_data.json

Usage:
    python3 tools/fetch_review_data.py
"""

import os
import json
import pickle
import base64
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, '.tmp')
OUTPUT_FILE = os.path.join(TMP_DIR, 'review_data.json')

EPS_TOKEN = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')
PERSONAL_TOKEN = os.path.join(BASE_DIR, 'projects', 'personal', 'token_personal_ai.pickle')
EPS_ENV = os.path.join(BASE_DIR, 'projects', 'eps', '.env')

os.makedirs(TMP_DIR, exist_ok=True)

load_dotenv(EPS_ENV)
PIPEDRIVE_API_KEY = os.getenv('PIPEDRIVE_API_KEY', '')
PIPEDRIVE_DOMAIN = os.getenv('PIPEDRIVE_COMPANY_DOMAIN', 'api.pipedrive.com')


def load_token(token_path):
    if not os.path.exists(token_path):
        return None
    with open(token_path, 'rb') as f:
        return pickle.load(f)


def fetch_gmail(token_path, label, max_results=50):
    creds = load_token(token_path)
    if not creds:
        print(f"  [{label}] No token found — skipping Gmail")
        return []

    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y/%m/%d')
        results = service.users().messages().list(
            userId='me',
            q=f'after:{cutoff}',
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        threads = []

        for msg in messages:
            detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
            threads.append({
                'subject': headers.get('Subject', '(no subject)'),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': detail.get('snippet', '')
            })

        print(f"  [{label}] Fetched {len(threads)} Gmail threads")
        return threads

    except Exception as e:
        print(f"  [{label}] Gmail fetch failed: {e}")
        return []


def fetch_calendar(token_path, label):
    creds = load_token(token_path)
    if not creds:
        print(f"  [{label}] No token found — skipping Calendar")
        return []

    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('calendar', 'v3', credentials=creds)

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=14)).isoformat()
        time_max = (now + timedelta(days=14)).isoformat()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        result = []
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date', ''))
            result.append({
                'title': e.get('summary', '(no title)'),
                'start': start,
                'description': e.get('description', '')[:200] if e.get('description') else ''
            })

        print(f"  [{label}] Fetched {len(result)} calendar events")
        return result

    except Exception as e:
        print(f"  [{label}] Calendar fetch failed: {e}")
        return []


def fetch_pipedrive(max_items=50):
    if not PIPEDRIVE_API_KEY:
        print("  [Pipedrive] No API key — skipping")
        return {'notes': [], 'activities': []}

    try:
        import urllib.request

        def pd_get(path):
            url = f"https://{PIPEDRIVE_DOMAIN}/v1/{path}&api_token={PIPEDRIVE_API_KEY}"
            with urllib.request.urlopen(url) as r:
                return json.loads(r.read())

        notes_data = pd_get(f"notes?limit={max_items}&sort=add_time+DESC")
        notes = [
            {
                'content': n.get('content', '')[:300],
                'added': n.get('add_time', ''),
                'deal': n.get('deal', {}).get('title', '') if n.get('deal') else ''
            }
            for n in (notes_data.get('data') or [])
        ]

        activities_data = pd_get(f"activities?limit={max_items}&sort=add_time+DESC")
        activities = [
            {
                'subject': a.get('subject', ''),
                'type': a.get('type', ''),
                'note': (a.get('note') or '')[:200],
                'due_date': a.get('due_date', ''),
                'deal': a.get('deal_title', '')
            }
            for a in (activities_data.get('data') or [])
        ]

        print(f"  [Pipedrive] Fetched {len(notes)} notes, {len(activities)} activities")
        return {'notes': notes, 'activities': activities}

    except Exception as e:
        print(f"  [Pipedrive] Fetch failed: {e}")
        return {'notes': [], 'activities': []}


def main():
    print("Fetching review data...")

    data = {
        'fetched_at': datetime.now().isoformat(),
        'gmail_eps': fetch_gmail(EPS_TOKEN, 'Gmail EPS'),
        'gmail_personal': fetch_gmail(PERSONAL_TOKEN, 'Gmail Personal'),
        'calendar_eps': fetch_calendar(EPS_TOKEN, 'Calendar EPS'),
        'pipedrive': fetch_pipedrive(),
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nDone. Output: {OUTPUT_FILE}")
    print(f"  gmail_eps:      {len(data['gmail_eps'])} threads")
    print(f"  gmail_personal: {len(data['gmail_personal'])} threads")
    print(f"  calendar_eps:   {len(data['calendar_eps'])} events")
    print(f"  pipedrive notes:{len(data['pipedrive']['notes'])}")
    print(f"  pipedrive acts: {len(data['pipedrive']['activities'])}")


if __name__ == '__main__':
    main()
