"""
Cold call follow-up automation.

Tracks warm leads from cold calls and sends a 4-email sequence (Day 0, 2, 5, 10).
Stops the sequence on any reply or manual mark-as-replied.

USAGE
-----
Add a new lead (after a cold call):
    python3 tools/cold_call_followup.py add \\
        --first-name "Mike" \\
        --company "Mike's Painting Co" \\
        --email "mike@mikespainting.com" \\
        --phone "+15551234567" \\
        --pain "slow quotes, leads going cold" \\
        --send-day0      # also fires the Day 0 email immediately

Run the daily check (cron this):
    python3 tools/cold_call_followup.py run            # dry-run
    python3 tools/cold_call_followup.py run --send     # actually send

Mark a lead as replied (stops the sequence):
    python3 tools/cold_call_followup.py reply --email "mike@mikespainting.com"

List active leads:
    python3 tools/cold_call_followup.py list

CONFIG
------
Edit CALENDAR_LINK and YOUR_PHONE below before first send.
Lead magnet PDF auto-attached to Day 0 from sales/lead-magnet.pdf.
"""

import argparse
import base64
import json
import mimetypes
import pickle
import sys
from datetime import datetime, timezone, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
LEADS_FILE = BASE_DIR / 'projects' / 'personal' / '.tmp' / 'cold_call_leads.json'
LEAD_MAGNET = BASE_DIR / 'projects' / 'personal' / 'sales' / 'lead-magnet.pdf'

FROM_EMAIL = 'allenenriquez.ai@gmail.com'
FROM_NAME = 'Allen Enriquez'

# EDIT THESE before first send
CALENDAR_LINK = 'https://calendar.app.google/your-link-here'
YOUR_PHONE = '+639454203195'
DEMO_VIDEO_LINK = '[your loom link here]'

SCHEDULE = [0, 2, 5, 10]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_iso(s):
    return datetime.fromisoformat(s)


def load_leads():
    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LEADS_FILE.exists():
        return []
    return json.loads(LEADS_FILE.read_text())


def save_leads(leads):
    LEADS_FILE.write_text(json.dumps(leads, indent=2))


def get_service():
    if not TOKEN_FILE.exists():
        print("ERROR: token missing. Run tools/auth_personal.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)


def render(template, lead):
    return (template
            .replace('{{first_name}}', lead['first_name'])
            .replace('{{company}}', lead['company'])
            .replace('{{specific_pain}}', lead.get('pain', 'the slow quote process'))
            .replace('{{calendar_link}}', CALENDAR_LINK)
            .replace('{{your_phone}}', YOUR_PHONE)
            .replace('{{demo_video}}', DEMO_VIDEO_LINK))


EMAILS = {
    0: {
        'subject': 'Quick PDF I mentioned — {{first_name}}',
        'body': """Hi {{first_name}},

Good chat earlier. As promised — here's the PDF I told you about.

5 things slowing down sales in painting companies. And how to fix each one with AI.

[PDF attached]

You said {{specific_pain}} was the biggest one. Take a look at #1 and #3 — that's where most painters get the fastest wins.

If you want me to set one up for you, here's my calendar:
{{calendar_link}}

Free 15-min call. No pitch. I'll just tell you what would fix it fastest.

Allen Enriquez
{{your_phone}}
""",
        'attach_pdf': True,
    },
    2: {
        'subject': 'Did you see #3?',
        'body': """Hi {{first_name}},

Quick one — did you get a chance to look at the PDF I sent?

#3 is the one most painters skip. The one about leads going quiet.

Most companies lose $20K-$50K a month on quiet leads. AI follow-up is the easiest fix. Takes 72 hours to set up.

Want me to walk you through how it works?

{{calendar_link}}

Allen
""",
    },
    5: {
        'subject': "Here's the system actually running",
        'body': """Hi {{first_name}},

I made a short video showing the AI quote builder running on a real job.

{{demo_video}}

This is the same system I use at my own painting company. Quote built in 4 minutes. Sent to the customer same day.

If you want one set up for {{company}}, pick a slot:
{{calendar_link}}

Allen
""",
    },
    10: {
        'subject': 'Last note from me',
        'body': """Hi {{first_name}},

I won't keep emailing — I know you're busy.

If timing's not right, that's all good. Just keep the PDF. The fixes still work even if you build them yourself.

If anything changes and you want help, my line's open:
{{your_phone}}
{{calendar_link}}

Either way, all the best with the season.

Allen
""",
    },
}


def build_message(to_email, subject, body, attach_pdf=False):
    msg = MIMEMultipart()
    msg['to'] = to_email
    msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attach_pdf and LEAD_MAGNET.exists():
        ctype, _ = mimetypes.guess_type(str(LEAD_MAGNET))
        maintype, subtype = (ctype or 'application/pdf').split('/', 1)
        with open(LEAD_MAGNET, 'rb') as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=LEAD_MAGNET.name)
        msg.attach(part)
    return msg


def send_email(to_email, subject, body, attach_pdf=False, dry_run=False):
    if dry_run:
        attach_note = f" [+ PDF: {LEAD_MAGNET.name}]" if attach_pdf else ""
        print(f"--- DRY RUN{attach_note} ---")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(body)
        print("--- END ---\n")
        return {'status': 'dry_run'}
    msg = build_message(to_email, subject, body, attach_pdf=attach_pdf)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = get_service()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return {'status': 'sent', 'message_id': result.get('id')}


def cmd_add(args):
    leads = load_leads()
    if any(l['email'].lower() == args.email.lower() for l in leads):
        print(f"Already tracking {args.email}", file=sys.stderr)
        sys.exit(1)
    lead = {
        'first_name': args.first_name,
        'company': args.company,
        'email': args.email,
        'phone': args.phone or '',
        'pain': args.pain or '',
        'added_at': now_iso(),
        'status': 'active',
        'sent': {},   # day -> iso timestamp
    }
    leads.append(lead)
    save_leads(leads)
    print(f"Added {args.first_name} ({args.company}) — {args.email}")

    if args.send_day0:
        send_for_day(lead, 0, send=args.send)
        leads = load_leads()
        for l in leads:
            if l['email'] == lead['email']:
                l['sent']['0'] = now_iso() if args.send else 'dry_run:' + now_iso()
        save_leads(leads)


def cmd_reply(args):
    leads = load_leads()
    found = False
    for l in leads:
        if l['email'].lower() == args.email.lower():
            l['status'] = 'replied'
            l['replied_at'] = now_iso()
            found = True
    if not found:
        print(f"No lead with email {args.email}", file=sys.stderr)
        sys.exit(1)
    save_leads(leads)
    print(f"Marked {args.email} as replied. Sequence stopped.")


def cmd_list(_args):
    leads = load_leads()
    if not leads:
        print("No leads tracked yet.")
        return
    for l in leads:
        days = sorted(int(k) for k in l.get('sent', {}).keys())
        sent = ','.join(f"D{d}" for d in days) or '-'
        print(f"[{l['status']:8}] {l['first_name']:<15} {l['company']:<30} {l['email']:<35} sent: {sent}")


def send_for_day(lead, day, send=False):
    cfg = EMAILS[day]
    subject = render(cfg['subject'], lead)
    body = render(cfg['body'], lead)
    attach = cfg.get('attach_pdf', False)
    return send_email(lead['email'], subject, body, attach_pdf=attach, dry_run=not send)


def cmd_run(args):
    leads = load_leads()
    now = datetime.now(timezone.utc)
    actions = 0
    for lead in leads:
        if lead['status'] != 'active':
            continue
        added = parse_iso(lead['added_at'])
        days_since = (now - added).days
        for day in SCHEDULE:
            if str(day) in lead.get('sent', {}):
                continue
            if days_since < day:
                continue
            print(f"=> {lead['first_name']} ({lead['email']}) — Day {day}")
            send_for_day(lead, day, send=args.send)
            lead.setdefault('sent', {})[str(day)] = now_iso() if args.send else 'dry_run:' + now_iso()
            actions += 1
            # Only fire one email per lead per run.
            break
        # Mark sequence done after Day 10
        if str(SCHEDULE[-1]) in lead.get('sent', {}):
            lead['status'] = 'sequence_done'
    if args.send:
        save_leads(leads)
    print(f"\n{actions} email(s) {'sent' if args.send else 'simulated (dry-run)'}.")
    if not args.send and actions:
        print("Run with --send to actually send.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='Add a new warm lead from a cold call')
    a.add_argument('--first-name', required=True, dest='first_name')
    a.add_argument('--company', required=True)
    a.add_argument('--email', required=True)
    a.add_argument('--phone', default='')
    a.add_argument('--pain', default='', help='What they said was their biggest issue')
    a.add_argument('--send-day0', action='store_true', dest='send_day0', help='Also send Day 0 email now')
    a.add_argument('--send', action='store_true', help='Actually send (otherwise dry-run when --send-day0)')
    a.set_defaults(func=cmd_add)

    r = sub.add_parser('reply', help='Mark lead as replied (stops sequence)')
    r.add_argument('--email', required=True)
    r.set_defaults(func=cmd_reply)

    l = sub.add_parser('list', help='List all tracked leads')
    l.set_defaults(func=cmd_list)

    run = sub.add_parser('run', help='Send any due emails (cron this)')
    run.add_argument('--send', action='store_true', help='Actually send. Without this, dry-run.')
    run.set_defaults(func=cmd_run)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
