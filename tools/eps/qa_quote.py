"""
QA agent for EPS quotes. Checks the quote and email draft before anything goes to the client.
Posts a QA report + email draft as a note on the Pipedrive deal for Allen to review.

Usage:
    python3 tools/qa_quote.py \\
        --template "quotes/builders_cleaning" \\
        --first-name "Allen" \\
        --to "allenenriquez.ai@gmail.com" \\
        --situation "7-townhouse project nearing completion, builder needs 3-stage clean before handover" \\
        --opener "Good talking to you earlier." \\
        --bonus "Window and glass cleaning across all 7 townhouses is included." \\
        --deal-id "1076" \\
        --doc-url "https://docs.google.com/document/d/..."

After Allen approves the note in Pipedrive, run draft_quote_email.py --send to send.
"""

import argparse
import json
import re
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
        print(f"ERROR: {QUOTE_DATA} not found.", file=sys.stderr)
        sys.exit(1)
    with open(QUOTE_DATA) as f:
        return json.load(f)


def load_template(template_key):
    path = TEMPLATES_DIR / f"{template_key}.txt"
    if not path.exists():
        return None
    return path.read_text()


def extract_scope_bullets(quote_data, max_bullets=5):
    items = quote_data.get('line_items', [])
    seen = set()
    bullets = []
    for item in items:
        desc = item.get('description', '')
        if desc and desc not in seen:
            seen.add(desc)
            bullets.append(desc)
    return bullets[:max_bullets]


def fill_template(template, fields):
    result = template
    for key, value in fields.items():
        result = result.replace(f'[{key}]', value or '')
    return result


def parse_subject_and_body(filled):
    lines = filled.splitlines()
    subject, body_start = '', 0
    for i, line in enumerate(lines):
        if line.startswith('SUBJECT:'):
            subject = line.replace('SUBJECT:', '').strip()
            body_start = i + 1
            break
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    body = '\n'.join(lines[body_start:]).strip()
    body_lines = [l for l in body.splitlines() if l.strip() not in ('- ', '-', '•')]
    return subject, '\n'.join(body_lines)


def run_qa(quote_data, subject, body, args):
    issues = []
    warnings = []

    # 1. Required fields present
    for field in ['client', 'address', 'job_type', 'quote_date', 'email']:
        if not quote_data.get(field):
            issues.append(f"Missing field in quote_data.json: {field}")

    # 1b. Check for unfilled placeholder values (not just presence)
    placeholder_values = {'client name', 'client', 'name', 'your name', 'client address', 'address', 'your address'}
    if quote_data.get('client', '').strip().lower() in placeholder_values:
        issues.append(f"'client' field contains placeholder text ('{quote_data['client']}') — use real client name from Pipedrive deal")
    if quote_data.get('address', '').strip().lower() in placeholder_values:
        issues.append(f"'address' field contains placeholder text ('{quote_data['address']}') — use real address from Pipedrive deal")

    # 2. Job description has content and all 7 required sections
    jd = quote_data.get('job_description', [])
    jd_text = '\n'.join(jd) if isinstance(jd, list) else str(jd)
    if len(jd_text.strip()) < 100:
        issues.append("Job description is too short or empty")
    for section in ['JOB SUMMARY', 'SCOPE OF WORK', 'INCLUSIONS', 'EXCLUSIONS']:
        if section not in jd_text.upper():
            issues.append(f"Job description missing required section: {section}")
    # Accept either CLEANING METHOD or PAINTING METHOD
    if 'CLEANING METHOD' not in jd_text.upper() and 'PAINTING METHOD' not in jd_text.upper():
        issues.append("Job description missing required section: CLEANING METHOD or PAINTING METHOD")
    # Accept either "PAYMENT TERMS" or "BOOKING & PAYMENT TERMS"
    if 'PAYMENT TERMS' not in jd_text.upper():
        issues.append("Job description missing required section: BOOKING & PAYMENT TERMS")

    # 3. Line items check
    line_items = quote_data.get('line_items', [])
    if not line_items:
        issues.append("No line items found")
    else:
        # Check math
        calculated_subtotal = round(sum(i.get('subtotal', 0) for i in line_items), 2)
        stated_subtotal = round(quote_data.get('subtotal', 0), 2)
        stated_gst = round(quote_data.get('gst', 0), 2)
        stated_total = round(quote_data.get('total', 0), 2)
        expected_gst = round(stated_subtotal * 0.1, 2)
        expected_total = round(stated_subtotal + stated_gst, 2)

        if calculated_subtotal != stated_subtotal:
            issues.append(f"Line items sum (${calculated_subtotal:,.2f}) ≠ stated subtotal (${stated_subtotal:,.2f})")
        if abs(stated_gst - expected_gst) > 0.02:
            issues.append(f"GST (${stated_gst:,.2f}) doesn't match 10% of subtotal (${expected_gst:,.2f})")
        if abs(stated_total - expected_total) > 0.02:
            issues.append(f"Total (${stated_total:,.2f}) ≠ subtotal + GST (${expected_total:,.2f})")

        # Warn if all line items have the same description (not split by component)
        descs = [i.get('description', '') for i in line_items]
        if len(set(descs)) < len(descs) * 0.5:
            warnings.append("Line items may not be split by component — consider per-unit breakdown")

    # 4. No unfilled placeholders in email
    placeholders = re.findall(r'\[[A-Za-z_][A-Za-z_0-9 ]*\]', body)
    if placeholders:
        issues.append(f"Unfilled placeholders in email: {', '.join(set(placeholders))}")

    # 5. Email length
    word_count = len(body.split())
    if word_count > 200:
        warnings.append(f"Email is {word_count} words — aim for under 180")

    # 6. Deal ID
    if not args.deal_id:
        warnings.append("No deal ID — email won't be linked to a Pipedrive deal")

    return issues, warnings


def _urls_to_links(text: str) -> str:
    """Convert 'Label — https://url' lines into HTML hyperlinks."""
    import re
    out = []
    for line in text.splitlines():
        m = re.match(r'^(-\s+)?(.+?)\s+[—–-]+\s+(https?://\S+)$', line)
        if m:
            bullet = m.group(1) or ''
            out.append(f'{bullet}<a href="{m.group(3)}">{m.group(2).strip()}</a>')
        else:
            out.append(line)
    return '\n'.join(out)


def post_note_to_pipedrive(deal_id, note_content, api_key, domain):
    import requests
    url = f"https://{domain}/v1/notes"
    payload = {
        "content": note_content,
        "deal_id": int(deal_id),
        "pinned_to_deal_flag": 1,
    }
    r = requests.post(url, params={'api_token': api_key}, json=payload)
    r.raise_for_status()
    data = r.json()
    if not data.get('success'):
        print(f"ERROR posting note: {data}", file=sys.stderr)
        sys.exit(1)
    return data['data']['id']


def main():
    parser = argparse.ArgumentParser(description='QA check for EPS quote + email draft. Posts result to Pipedrive.')
    parser.add_argument('--template', default='')
    parser.add_argument('--first-name', default='', dest='first_name')
    parser.add_argument('--to', default='')
    parser.add_argument('--situation', default='')
    parser.add_argument('--concern-1', default='', dest='concern_1')
    parser.add_argument('--concern-2', default='', dest='concern_2')
    parser.add_argument('--opener', default='It was great talking to you.')
    parser.add_argument('--bonus', default='')
    parser.add_argument('--deal-id', default='', dest='deal_id')
    parser.add_argument('--doc-url', default='', dest='doc_url')
    parser.add_argument('--data-only', action='store_true', dest='data_only',
                        help='Validate quote_data.json only (job description + line items). '
                             'Use before creating the Google Doc. Does not need email template args.')
    args = parser.parse_args()

    env = load_env()
    quote_data = load_quote_data()

    # --data-only: validate quote data before creating the Google Doc
    if args.data_only:
        issues, warnings = run_qa(quote_data, '', '', args)
        # Filter out email-related issues when running data-only
        issues = [i for i in issues if 'placeholder' not in i.lower() and 'word' not in i.lower()]
        warnings = [w for w in warnings if 'placeholder' not in w.lower() and 'word' not in w.lower()]
        status = "❌ FAILED" if issues else ("⚠️ PASSED WITH WARNINGS" if warnings else "✅ PASSED")
        print(f"\nDATA QA: {status}")
        if issues:
            print("\nISSUES (fix before creating Google Doc):")
            for i in issues:
                print(f"  ✗ {i}")
        if warnings:
            print("\nWARNINGS:")
            for w in warnings:
                print(f"  ⚠ {w}")
        print()
        if issues:
            sys.exit(1)
        return

    if not args.template:
        print("ERROR: --template required unless using --data-only", file=sys.stderr)
        sys.exit(1)
    if not args.first_name:
        print("ERROR: --first-name required unless using --data-only", file=sys.stderr)
        sys.exit(1)
    if not args.to:
        print("ERROR: --to required unless using --data-only", file=sys.stderr)
        sys.exit(1)

    template_raw = load_template(args.template)
    if not template_raw:
        print(f"ERROR: Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    scope_bullets = extract_scope_bullets(quote_data)
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
        'senderName': env.get('PIPEDRIVE_FROM_NAME', 'Allen — EPS Painting & Cleaning'),
        'service_label': quote_data.get('job_type', 'Quote'),
    }

    filled = fill_template(template_raw, fields)
    subject, body = parse_subject_and_body(filled)

    issues, warnings = run_qa(quote_data, subject, body, args)

    # Build QA report
    status = "❌ FAILED" if issues else ("⚠️ PASSED WITH WARNINGS" if warnings else "✅ PASSED")
    total_str = f"${quote_data.get('total', 0):,.2f} inc GST"

    report_lines = [
        f"<h3>📋 Quote QA Report — {status}</h3>",
        f"<b>Client:</b> {quote_data.get('client')} | <b>Job:</b> {quote_data.get('job_type')} | <b>Total:</b> {total_str}",
    ]
    if args.doc_url:
        report_lines.append(f"<b>Quote Doc:</b> <a href='{args.doc_url}'>View Google Doc</a>")
    report_lines.append("")

    if issues:
        report_lines.append("<b>🔴 Issues (must fix before sending):</b>")
        for i in issues:
            report_lines.append(f"• {i}")
        report_lines.append("")

    if warnings:
        report_lines.append("<b>🟡 Warnings:</b>")
        for w in warnings:
            report_lines.append(f"• {w}")
        report_lines.append("")

    report_lines += [
        "<hr>",
        f"<h4>📧 Email Draft</h4>",
        f"<b>To:</b> {args.to}<br>",
        f"<b>Subject:</b> {subject}<br><br>",
        _urls_to_links(body).replace('\n', '<br>'),
        "<hr>",
        "<i>To send: run draft_quote_email.py with --send once approved.</i>",
    ]

    note_content = '\n'.join(report_lines)

    # Print to terminal
    print(f"\n{'='*60}")
    print(f"QA STATUS: {status}")
    if issues:
        print("\nISSUES:")
        for i in issues: print(f"  ✗ {i}")
    if warnings:
        print("\nWARNINGS:")
        for w in warnings: print(f"  ⚠ {w}")
    print(f"\nSUBJECT: {subject}")
    print(f"TO: {args.to}")
    print('='*60)
    print(body)
    print('='*60)

    # Post to Pipedrive if deal ID provided
    if args.deal_id and env.get('PIPEDRIVE_API_KEY'):
        note_id = post_note_to_pipedrive(
            args.deal_id,
            note_content,
            env['PIPEDRIVE_API_KEY'],
            env.get('PIPEDRIVE_COMPANY_DOMAIN', 'api.pipedrive.com'),
        )
        print(f"\n✓ QA report + email draft posted to Pipedrive deal #{args.deal_id} (note #{note_id})")
        print("Review in Pipedrive, then run draft_quote_email.py --send to send.")
    else:
        print("\n(No deal ID — note not posted to Pipedrive)")

    if issues:
        sys.exit(1)


if __name__ == '__main__':
    main()
