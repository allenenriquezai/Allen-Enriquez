"""
Draft (and optionally send) a quote email for EPS.

Loads the right template from projects/eps/templates/email/,
fills variables from quote_data.json + CLI args, prints a preview,
and sends via Gmail API if --send is passed.

Usage:
    python3 tools/draft_quote_email.py \\
        --template "quotes/residential_painting" \\
        --first-name "Jane" \\
        --to "jane@example.com" \\
        --situation "selling in 6 weeks, wants a fresh look" \\
        --concern-1 "Will it be done before the open home?" \\
        --concern-2 "How disruptive will the painters be?" \\
        --opener "It was great chatting with you earlier." \\
        --bonus "We'll include a complimentary ceiling repaint in the living room." \\
        --deal-id "123" \\
        [--send]

Template keys (quotes/):
    quotes/residential_painting
    quotes/residential_cleaning
    quotes/builders_cleaning
    quotes/builders_painting
    quotes/builders_painting_cleaning
    quotes/bond_clean
"""

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
QUOTE_DATA = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'quote_data.json'
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


def load_quote_data():
    if not QUOTE_DATA.exists():
        print(f"ERROR: {QUOTE_DATA} not found. Run calculate_quote.py first.", file=sys.stderr)
        sys.exit(1)
    with open(QUOTE_DATA) as f:
        return json.load(f)


def load_template(template_key: str) -> str:
    path = TEMPLATES_DIR / f"{template_key}.txt"
    if not path.exists():
        print(f"ERROR: Template not found: {path}", file=sys.stderr)
        print("Available templates:", file=sys.stderr)
        for t in sorted(TEMPLATES_DIR.rglob('*.txt')):
            print(f"  {t.relative_to(TEMPLATES_DIR).with_suffix('')}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def extract_scope_bullets(quote_data: dict, max_bullets: int = 5) -> list:
    """Pull description from each line item (skip complimentary $0 items last if over limit)."""
    items = quote_data.get('line_items', [])
    bullets = [item['description'] for item in items if item.get('description')]
    return bullets[:max_bullets]


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
    # Skip blank lines after subject
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    body = '\n'.join(lines[body_start:]).strip()
    return subject, body


def to_html(plain_body: str) -> str:
    """Convert plain text body to HTML. Turns 'Label — https://url' into hyperlinks."""
    import re
    html_lines = []
    for line in plain_body.splitlines():
        # Convert "Label — https://url" or "Label - https://url" to a hyperlink
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
    parser = argparse.ArgumentParser(description='Draft and optionally send an EPS quote email.')
    parser.add_argument('--template', required=True,
                        help='Template key, e.g. quotes/residential_painting')
    parser.add_argument('--first-name', required=True, help='Client first name')
    parser.add_argument('--to', required=True, help='Client email address')
    parser.add_argument('--situation', default='',
                        help='1-sentence recap of their situation and desired outcome')
    parser.add_argument('--concern-1', default='', dest='concern_1',
                        help='First buying concern (residential templates)')
    parser.add_argument('--concern-2', default='', dest='concern_2',
                        help='Second buying concern (residential templates)')
    parser.add_argument('--opener', default='It was great talking to you.',
                        help='1-line personal opener')
    parser.add_argument('--bonus', default='',
                        help='Complimentary/bonus item to highlight (optional)')
    parser.add_argument('--deal-id', default='', dest='deal_id',
                        help='Pipedrive deal ID to link the email to')
    parser.add_argument('--send', action='store_true',
                        help='Send the email after previewing (default: preview only)')
    parser.add_argument('--pdf-name', default='', dest='pdf_name',
                        help='Override PDF attachment filename shown to client (e.g. "EPS_Quote_Jane.pdf")')
    args = parser.parse_args()

    env = load_env()
    quote_data = load_quote_data()
    template_raw = load_template(args.template)

    scope_bullets = extract_scope_bullets(quote_data)
    # Pad to 5 slots so unfilled ones become empty strings
    scope_bullets += [''] * (5 - len(scope_bullets))

    fields = {
        'firstName': args.first_name,
        'opener': args.opener,
        'situation': args.situation,
        'concern_1': args.concern_1,
        'concern_2': args.concern_2,
        'scope_bullet_1': scope_bullets[0],
        'scope_bullet_2': scope_bullets[1],
        'scope_bullet_3': scope_bullets[2],
        'scope_bullet_4': scope_bullets[3],
        'scope_bullet_5': scope_bullets[4],
        'bonus_line': args.bonus,
        'address': quote_data.get('address', ''),
        'senderName': env.get('GMAIL_FROM_NAME', 'Allen — EPS Painting & Cleaning'),
        'service_label': quote_data.get('job_type', 'Quote'),
    }

    filled = fill_template(template_raw, fields)
    subject, body = parse_subject_and_body(filled)

    # Clean up empty bullet lines (lines that are just "- ") and collapse multiple blank lines
    body_lines = [
        line for line in body.splitlines()
        if not (line.strip() in ('- ', '-', '•'))
    ]
    # Collapse consecutive blank lines into one
    collapsed = []
    prev_blank = False
    for line in body_lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = is_blank
    body = '\n'.join(collapsed)

    print('\n' + '=' * 60)
    print('SUBJECT:', subject)
    print('TO:', args.to)
    if args.deal_id:
        print('DEAL ID:', args.deal_id)
    print('=' * 60)
    print(body)
    print('=' * 60 + '\n')

    if not args.send:
        print('--- PREVIEW ONLY — add --send to send this email ---')
        return

    # Import send logic directly
    sys.path.insert(0, str(BASE_DIR / 'tools'))
    from send_email_gmail import send_email

    pdf_path = BASE_DIR / 'projects' / 'eps' / '.tmp' / 'quote_output.pdf'
    attachment = str(pdf_path) if pdf_path.exists() else None
    if attachment:
        # Use --pdf-name if provided, else use quote_title from quote_data, else fallback
        quote_title = quote_data.get('quote_title', '').strip()
        safe_title = quote_title.replace('/', '-').replace('\\', '-') if quote_title else ''
        pdf_display_name = args.pdf_name or (f"{safe_title}.pdf" if safe_title else 'EPS_Quote.pdf')
        # Copy with new name so the attachment filename is client-facing
        import shutil
        renamed_path = pdf_path.parent / pdf_display_name
        shutil.copy2(str(pdf_path), str(renamed_path))
        attachment = str(renamed_path)
        print(f"Attaching PDF: {pdf_display_name}")
    else:
        print("WARNING: No PDF found at .tmp/quote_output.pdf — sending without attachment.")
        print("Run: python3 tools/export_quote_pdf.py --doc-id DOC_ID first.")

    result = send_email(
        to_email=args.to,
        subject=subject,
        body=to_html(body),
        deal_id=args.deal_id or None,
        html=True,
        attachment_path=attachment,
    )
    print(f"Sent successfully. Message ID: {result.get('id')}")
    if args.deal_id:
        print(f"Note: will auto-sync to Pipedrive deal #{args.deal_id} if Gmail inbox is connected")


if __name__ == '__main__':
    main()
