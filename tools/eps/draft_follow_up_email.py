"""
Draft (and optionally send) a follow-up email for EPS.

Reads deal info from Pipedrive (if deal-id provided), fills the right
follow-up template, prints a preview, and sends via Pipedrive if --send is passed.

Usage:
    python3 tools/draft_follow_up_email.py \\
        --deal-id "1076" \\
        --template "follow_ups/builders_cleaning" \\
        --first-name "Jane" \\
        --to "jane@example.com" \\
        --opener "Hope the project is coming along well." \\
        [--new-info "We've also just become available earlier than expected."] \\
        [--send]

Template keys (follow_ups/):
    follow_ups/builders_cleaning
    follow_ups/builders_painting
    follow_ups/residential_painting
    follow_ups/residential_cleaning
"""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / 'projects' / 'eps' / 'templates' / 'email'
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def load_template(template_key: str) -> str:
    path = TEMPLATES_DIR / f"{template_key}.txt"
    if not path.exists():
        print(f"ERROR: Template not found: {path}", file=sys.stderr)
        print("Available templates:", file=sys.stderr)
        for t in sorted(TEMPLATES_DIR.rglob('*.txt')):
            print(f"  {t.relative_to(TEMPLATES_DIR).with_suffix('')}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def get_deal_from_pipedrive(deal_id: str, api_key: str, domain: str) -> dict:
    import urllib.request
    url = f"https://{domain}/v1/deals/{deal_id}?api_token={api_key}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        if not data.get('success'):
            return {}
        d = data['data']
        person = d.get('person_id') or {}
        return {
            'title': d.get('title', ''),
            'first_name': (person.get('name') or '').split()[0] if person.get('name') else '',
            'email': (person.get('email') or [{}])[0].get('value', '') if person.get('email') else '',
            'value': d.get('value', 0),
            'stage': (d.get('stage_id') or ''),
        }
    except Exception as e:
        print(f"Warning: Could not fetch deal {deal_id} from Pipedrive: {e}", file=sys.stderr)
        return {}


def fill_template(template: str, fields: dict) -> str:
    result = template
    for key, value in fields.items():
        result = result.replace(f'[{key}]', value or '')
    return result


def parse_subject_and_body(filled: str) -> tuple[str, str]:
    lines = filled.splitlines()
    subject = ''
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('SUBJECT:'):
            subject = line.replace('SUBJECT:', '').strip()
            body_start = i + 1
            break
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    body = '\n'.join(lines[body_start:]).strip()
    # Remove empty bullet lines
    body = '\n'.join(l for l in body.splitlines() if l.strip() not in ('- ', '-', '•', '[new_info]'))
    return subject, body


def post_note_to_pipedrive(deal_id: str, note_content: str, api_key: str, domain: str) -> int:
    import urllib.request
    url = f"https://{domain}/v1/notes?api_token={api_key}"
    payload = json.dumps({
        "content": note_content,
        "deal_id": int(deal_id),
        "pinned_to_deal_flag": 1,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    if not data.get('success'):
        print(f"ERROR posting note: {data}", file=sys.stderr)
        sys.exit(1)
    return data['data']['id']


def to_html(plain_body: str) -> str:
    import re
    html_lines = []
    for line in plain_body.splitlines():
        match = re.match(r'^(-\s+)?(.+?)\s+[—–-]+\s+(https?://\S+)$', line)
        if match:
            bullet = match.group(1) or ''
            label = match.group(2).strip()
            url = match.group(3).strip()
            html_lines.append(f'{bullet}<a href="{url}">{label}</a>')
        else:
            html_lines.append(line)
    return '<br>\n'.join(html_lines)


def main():
    parser = argparse.ArgumentParser(description='Draft and optionally send an EPS follow-up email.')
    parser.add_argument('--deal-id', required=True, dest='deal_id', help='Pipedrive deal ID')
    parser.add_argument('--template', required=True, help='Template key, e.g. follow_ups/builders_cleaning')
    parser.add_argument('--first-name', default='', dest='first_name', help='Client first name (auto-read from Pipedrive if blank)')
    parser.add_argument('--to', default='', help='Client email (auto-read from Pipedrive if blank)')
    parser.add_argument('--opener', default='', help='1-line opener referencing the original call or quote')
    parser.add_argument('--new-info', default='', dest='new_info', help='Any new info since the quote was sent (optional)')
    parser.add_argument('--send', action='store_true', help='Send the email (default: preview only)')
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN', 'api.pipedrive.com')

    # Try to fill missing name/email from Pipedrive
    first_name = args.first_name
    to_email = args.to
    address = ''
    service_label = 'Quote'

    if api_key and args.deal_id:
        deal = get_deal_from_pipedrive(args.deal_id, api_key, domain)
        if deal:
            if not first_name:
                first_name = deal.get('first_name', '')
            if not to_email:
                to_email = deal.get('email', '')
            address = deal.get('title', '')
            service_label = deal.get('title', 'Quote')

    if not first_name:
        print("ERROR: --first-name required (or provide --deal-id so it can be read from Pipedrive)", file=sys.stderr)
        sys.exit(1)
    if not to_email:
        print("ERROR: --to required (or provide --deal-id so it can be read from Pipedrive)", file=sys.stderr)
        sys.exit(1)

    template_raw = load_template(args.template)

    fields = {
        'firstName': first_name,
        'opener': args.opener,
        'new_info': args.new_info,
        'address': address,
        'service_label': service_label,
        'senderName': env.get('PIPEDRIVE_FROM_NAME', 'Allen — EPS Painting & Cleaning'),
    }

    filled = fill_template(template_raw, fields)
    subject, body = parse_subject_and_body(filled)

    word_count = len(body.split())

    print('\n' + '=' * 60)
    print('SUBJECT:', subject)
    print('TO:', to_email)
    print('DEAL ID:', args.deal_id)
    print(f'WORD COUNT: {word_count}', '⚠️  over 120' if word_count > 120 else '')
    print('=' * 60)
    print(body)
    print('=' * 60 + '\n')

    if not args.send:
        # Post draft as pinned note to Pipedrive for review
        if api_key and args.deal_id:
            note_lines = [
                "<h3>📧 Follow-Up Email Draft — Awaiting Approval</h3>",
                f"<b>To:</b> {to_email}<br>",
                f"<b>Subject:</b> {subject}<br><br>",
                body.replace('\n', '<br>'),
                "<hr>",
                "<i>To send: run draft_follow_up_email.py with --send once approved.</i>",
            ]
            note_id = post_note_to_pipedrive(args.deal_id, '\n'.join(note_lines), api_key, domain)
            print(f"Draft posted to Pipedrive deal #{args.deal_id} (note #{note_id})")
            print("Review in Pipedrive, then run with --send to send.")
        else:
            print('--- PREVIEW ONLY — add --send to send this email ---')
        return

    sys.path.insert(0, str(BASE_DIR / 'tools'))
    from send_email_gmail import send_email

    send_email(
        to_email=to_email,
        subject=subject,
        body=to_html(body),
        deal_id=args.deal_id or None,
        html=True,
    )
    print(f"Sent to {to_email}.")
    print(f"Linked to Pipedrive deal #{args.deal_id}")


if __name__ == '__main__':
    main()
