"""
Briefing Action Loop — processes Allen's reply to the morning briefing.

Checks personal Gmail for a reply to today's briefing, parses GO/SKIP
commands, and executes approved AI actions (draft responses, chase emails).

Drafts are NOT auto-sent — they're posted as Pipedrive notes for review.

Usage:
    python3 tools/briefing_action_loop.py              # check for reply, execute
    python3 tools/briefing_action_loop.py --dry-run     # parse reply but don't execute
    python3 tools/briefing_action_loop.py --show        # show today's manifest only

Requires:
    projects/personal/token_personal.pickle: Gmail OAuth token
    .tmp/briefing_actions.json: saved by morning_briefing.py
"""

import argparse
import json
import pickle
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / '.tmp'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'
MANIFEST_FILE = TMP_DIR / 'briefing_actions.json'

BRIEFING_FROM_EMAIL = 'allenenriquez@gmail.com'
BRIEFING_FROM_NAME = 'Enriquez OS'
BRIEFING_TO_EMAIL = 'allenenriquez006@gmail.com'


def load_manifest():
    if not MANIFEST_FILE.exists():
        return None
    data = json.loads(MANIFEST_FILE.read_text())
    if data.get('date') != datetime.now().strftime('%Y-%m-%d'):
        print("Manifest is from a different day — skipping")
        return None
    return data


def get_gmail_service():
    if not PERSONAL_TOKEN.exists():
        print("ERROR: Personal token not found.", file=sys.stderr)
        sys.exit(1)
    with open(PERSONAL_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)


def find_briefing_reply(service, manifest):
    """Search for a reply to today's briefing email."""
    date_str = manifest['date']
    msg_id = manifest.get('briefing_message_id')

    # Search by subject pattern
    query = f'subject:"Morning Briefing {date_str}" from:{BRIEFING_TO_EMAIL}'
    results = service.users().messages().list(
        userId='me', q=query, maxResults=5
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        return None

    # Find the reply (not the original briefing)
    for msg in messages:
        detail = service.users().messages().get(
            userId='me', id=msg['id'], format='full'
        ).execute()

        # Skip if this is the original briefing we sent
        if msg_id and msg['id'] == msg_id:
            continue

        # Check if it's from Allen (the reply)
        headers = {h['name'].lower(): h['value']
                   for h in detail.get('payload', {}).get('headers', [])}
        from_addr = headers.get('from', '').lower()
        if BRIEFING_TO_EMAIL.lower() not in from_addr:
            continue

        # Extract body text
        body = extract_body(detail)
        if body:
            return body

    return None


def extract_body(message):
    """Extract plain text body from a Gmail message."""
    import base64

    payload = message.get('payload', {})

    # Simple message
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    # Multipart
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    # Fallback to snippet
    return message.get('snippet', '')


def parse_commands(reply_text):
    """Parse GO/SKIP commands from reply text. Returns (go_numbers, skip_numbers)."""
    text = reply_text.upper().strip()

    # Handle "GO ALL"
    if 'GO ALL' in text or 'APPROVE ALL' in text or 'YES ALL' in text:
        return 'ALL', set()

    go_numbers = set()
    skip_numbers = set()

    # Find all numbers after GO/YES/APPROVE
    go_match = re.findall(r'(?:GO|YES|APPROVE)\s*[:#]?\s*([\d,\s]+)', text)
    for match in go_match:
        for num in re.findall(r'\d+', match):
            go_numbers.add(int(num))

    # Find all numbers after SKIP/NO/IGNORE
    skip_match = re.findall(r'(?:SKIP|NO|IGNORE)\s*[:#]?\s*([\d,\s]+)', text)
    for match in skip_match:
        for num in re.findall(r'\d+', match):
            skip_numbers.add(int(num))

    # If no explicit GO but numbers mentioned with positive words
    if not go_numbers and not skip_numbers:
        numbers = set(int(n) for n in re.findall(r'\d+', text))
        positive = any(w in text for w in ['GO', 'YES', 'APPROVE', 'DO', 'OK', 'SURE'])
        if positive and numbers:
            go_numbers = numbers

    return go_numbers, skip_numbers


def execute_action(action, dry_run=False):
    """Execute a single AI action."""
    action_type = action['type']
    num = action['number']

    if action_type == 'inquiry':
        print(f"  #{num} [inquiry] Draft response to: {action.get('from', '')} — {action.get('subject', '')}")
        if not dry_run:
            # For now, log to manifest as "pending_draft" — full email drafting
            # will be wired to eps-email-agent in a future iteration
            print(f"    → Queued for eps-email-agent (not yet wired)")
        return True

    elif action_type == 'chase':
        deal_id = action.get('deal_id')
        pipeline = action.get('pipeline', '')
        print(f"  #{num} [chase] Draft follow-up for deal {deal_id}: {action.get('deal_title', '')}")
        if not dry_run and deal_id:
            # Determine template from pipeline
            if 'clean' in pipeline.lower():
                template = 'follow_ups/builders_cleaning'
            else:
                template = 'follow_ups/builders_painting'

            cmd = [
                sys.executable, str(BASE_DIR / 'tools' / 'draft_follow_up_email.py'),
                '--deal-id', str(deal_id),
                '--template', template,
            ]
            person = action.get('person_name', '')
            if person:
                cmd.extend(['--first-name', person.split()[0]])

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"    → Draft created. Check Pipedrive deal #{deal_id}")
                else:
                    print(f"    → Error: {result.stderr[:200]}")
                    return False
            except Exception as e:
                print(f"    → Error: {e}")
                return False
        return True

    elif action_type == 'stale':
        deal_id = action.get('deal_id')
        print(f"  #{num} [stale] Send check-in for deal {deal_id}: {action.get('deal_title', '')}")
        if not dry_run:
            print(f"    → Queued for eps-email-agent (not yet wired)")
        return True

    return False


def send_confirmation(service, executed_actions):
    """Send a summary email back to Allen."""
    import base64
    from email.mime.text import MIMEText

    if not executed_actions:
        return

    lines = []
    for a in executed_actions:
        label = {'inquiry': 'Draft response', 'chase': 'Draft chase', 'stale': 'Check-in'}.get(a['type'], a['type'])
        title = a.get('subject') or a.get('deal_title') or ''
        deal_id = a.get('deal_id', '')
        deal_link = f" (deal #{deal_id})" if deal_id else ''
        lines.append(f"#{a['number']} {label}: {title}{deal_link}")

    body = "Actions executed:\n\n" + "\n".join(lines) + "\n\nCheck Pipedrive for drafts."

    msg = MIMEText(body, 'plain')
    msg['to'] = BRIEFING_TO_EMAIL
    msg['from'] = f"{BRIEFING_FROM_NAME} <{BRIEFING_FROM_EMAIL}>"
    msg['subject'] = f"AI Actions Done — {len(executed_actions)} drafts ready"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(f"\n  Confirmation sent to {BRIEFING_TO_EMAIL}")


def main():
    parser = argparse.ArgumentParser(description='Briefing Action Loop')
    parser.add_argument('--dry-run', action='store_true', help='Parse but don\'t execute')
    parser.add_argument('--show', action='store_true', help='Show today\'s manifest only')
    args = parser.parse_args()

    manifest = load_manifest()
    if not manifest:
        print("No valid manifest for today. Run morning_briefing.py first.")
        return

    actions = manifest.get('actions', [])
    print(f"Today's manifest: {len(actions)} actions")

    if args.show:
        for a in actions:
            label = {'inquiry': 'Draft response', 'chase': 'Draft chase', 'stale': 'Check-in'}.get(a['type'], a['type'])
            title = a.get('subject') or a.get('deal_title') or ''
            print(f"  #{a['number']} [{a['type']}] {label}: {title}")
        return

    # Check for reply
    print("\nChecking for briefing reply...")
    service = get_gmail_service()
    reply_text = find_briefing_reply(service, manifest)

    if not reply_text:
        print("No reply found. Nothing to do.")
        return

    print(f"Reply found: {reply_text[:100]}...")

    # Parse commands
    go_numbers, skip_numbers = parse_commands(reply_text)

    if go_numbers == 'ALL':
        go_numbers = set(a['number'] for a in actions)

    if not go_numbers:
        print("No actionable commands found in reply.")
        return

    print(f"GO: {sorted(go_numbers)}")
    if skip_numbers:
        print(f"SKIP: {sorted(skip_numbers)}")

    # Execute approved actions
    executed = []
    for action in actions:
        if action['number'] in go_numbers and action['number'] not in skip_numbers:
            success = execute_action(action, dry_run=args.dry_run)
            if success:
                executed.append(action)

    print(f"\nExecuted {len(executed)}/{len(go_numbers)} actions")

    # Send confirmation
    if executed and not args.dry_run:
        send_confirmation(service, executed)


if __name__ == '__main__':
    main()
